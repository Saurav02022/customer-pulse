"""The assessment lifecycle for one relationship: reuse, generate, check, store.

Database work runs in short sessions in the thread pool. No transaction is open while
the provider call is waiting. Only validated outcomes are stored; every failure is
raised to the caller and nothing is written for it. There is no retry here: the provider
owns its one retry, and a new request is the only other way to try again.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import Engine, delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.assessment.contract import (
    RESPONSE_SCHEMA,
    ActionNeeded,
    InsufficientEvidence,
    InvalidOutput,
    ModelResult,
    NoActionNeeded,
    Waiting,
    parse_reply,
)
from app.assessment.grounding import check_grounding
from app.assessment.model_input import build_model_input, canonical_json, fingerprint
from app.assessment.prompt import PROMPT_VERSION, SYSTEM_INSTRUCTION
from app.assessment.provider import (
    AssessmentProvider,
    ProviderEmptyResponse,
    ProviderError,
    ProviderTimeout,
)
from app.db import Assessment, Contact, Customer, CustomerStatus, Interaction

log = logging.getLogger(__name__)


class RelationshipNotFound(Exception):
    """No customer has this id."""


@dataclass(frozen=True)
class Unavailable:
    """Assessment unavailable, with a known cause. Not a business state."""

    cause: Literal["no_interactions", "insufficient_evidence"]


type BusinessResult = ActionNeeded | Waiting | NoActionNeeded
type AssessmentOutcome = BusinessResult | Unavailable


@dataclass(frozen=True)
class _Facts:
    status: CustomerStatus
    contacts: list[Contact]
    interactions: list[Interaction]


def _load_facts(engine: Engine, customer_id: str) -> _Facts | None:
    with Session(engine) as session:
        customer = session.get(Customer, customer_id)
        if customer is None:
            return None
        contacts = session.scalars(
            select(Contact).where(Contact.customer_id == customer_id)
        ).all()
        interactions = session.scalars(
            select(Interaction).where(Interaction.customer_id == customer_id)
        ).all()
        return _Facts(customer.status, list(contacts), list(interactions))


def _read_stored(engine: Engine, customer_id: str, key: str) -> str | None:
    with Session(engine) as session:
        return session.scalar(
            select(Assessment.result_json).where(
                Assessment.customer_id == customer_id, Assessment.fingerprint == key
            )
        )


def _delete_corrupt(engine: Engine, customer_id: str, key: str, stored: str) -> None:
    # Matching on the stored text too means a valid row written by a racing
    # request in the meantime is never removed.
    with Session(engine) as session, session.begin():
        session.execute(
            delete(Assessment).where(
                Assessment.customer_id == customer_id,
                Assessment.fingerprint == key,
                Assessment.result_json == stored,
            )
        )


def _store(engine: Engine, row: dict[str, object]) -> str:
    """Insert unless a row for this fingerprint exists, then return the stored text.

    Racing requests all return whichever row was stored first.
    """
    with Session(engine) as session, session.begin():
        session.execute(insert(Assessment).values(row).on_conflict_do_nothing())
        return session.scalars(
            select(Assessment.result_json).where(
                Assessment.customer_id == row["customer_id"],
                Assessment.fingerprint == row["fingerprint"],
            )
        ).one()


def _outcome(result: ModelResult) -> AssessmentOutcome:
    if isinstance(result, InsufficientEvidence):
        return Unavailable("insufficient_evidence")
    return result


def _outcome_name(result: ModelResult) -> str:
    if isinstance(result, InsufficientEvidence):
        return "insufficient_evidence"
    return f"assessed state={result.state}"


def _log(**fields: object) -> None:
    # Ids, categories and the state only. Never notes, prompts, input or replies.
    log.info("assessment %s", " ".join(f"{k}={v}" for k, v in fields.items()))


async def get_or_create_assessment(
    engine: Engine, provider: AssessmentProvider, customer_id: str
) -> AssessmentOutcome:
    """Return the assessment outcome for one relationship.

    Raises RelationshipNotFound, ProviderTimeout, ProviderError,
    ProviderEmptyResponse or InvalidOutput. None of those store anything.
    """
    attempt = {"attempt_id": uuid.uuid4().hex[:12], "customer_id": customer_id}

    facts = await run_in_threadpool(_load_facts, engine, customer_id)
    if facts is None:
        raise RelationshipNotFound(customer_id)
    # Decided in code, with no AI call and nothing stored.
    if not facts.interactions:
        _log(**attempt, outcome="no_interactions")
        return Unavailable("no_interactions")
    if not any(i.notes.strip() for i in facts.interactions):
        _log(**attempt, outcome="insufficient_evidence", decided="code")
        return Unavailable("insufficient_evidence")

    model_input, evidence = build_model_input(
        facts.status, facts.contacts, facts.interactions
    )
    key = fingerprint(model_input, provider.name, provider.model)
    attempt |= {
        "fingerprint": key[:12],
        "provider": provider.name,
        "model": provider.model,
        "prompt_version": PROMPT_VERSION,
    }

    stored = await run_in_threadpool(_read_stored, engine, customer_id, key)
    if stored is not None:
        try:
            result = parse_reply(stored)
        except InvalidOutput as error:
            # Derived cache data that no longer reads back. Drop only this row and
            # assess again.
            _log(**attempt, cache="corrupt", check=error.check)
            await run_in_threadpool(_delete_corrupt, engine, customer_id, key, stored)
        else:
            _log(**attempt, cache="hit", outcome=_outcome_name(result))
            return _outcome(result)

    try:
        raw = await provider.generate(
            SYSTEM_INSTRUCTION, canonical_json(model_input), RESPONSE_SCHEMA
        )
        result = check_grounding(parse_reply(raw), evidence)
    except InvalidOutput as error:
        check = f"{error.check}:{error.path}" if error.path else error.check
        _log(**attempt, cache="miss", outcome="invalid_output", check=check)
        raise
    except ProviderEmptyResponse:
        _log(**attempt, cache="miss", outcome="invalid_output", check="empty")
        raise
    except ProviderTimeout:
        _log(**attempt, cache="miss", outcome="provider_timeout")
        raise
    except ProviderError:
        _log(**attempt, cache="miss", outcome="provider_error")
        raise

    winner = await run_in_threadpool(
        _store,
        engine,
        {
            "customer_id": customer_id,
            "fingerprint": key,
            "result_json": result.model_dump_json(),
            "provider": provider.name,
            "model": provider.model,
            "prompt_version": PROMPT_VERSION,
            "created_at": datetime.now(UTC),
        },
    )
    stored_result = parse_reply(winner)
    _log(**attempt, cache="miss", outcome=_outcome_name(stored_result))
    return _outcome(stored_result)
