"""The assessment lifecycle with a fake provider and a temporary SQLite file.

No test calls a real model or opens the developer's customer_pulse.db.
"""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from assessment_support import (
    E_EMPTY_NOTE,
    E_FOREIGN,
    E_PRICING_SENT,
    EMPTY_NOTES_ID,
    NO_INTERACTIONS_ID,
    RELATIONSHIP_ID,
    FakeProvider,
    action_needed_reply,
    claim,
    fact_snapshot,
    insufficient_evidence_reply,
    no_action_needed_reply,
    sample_input,
    store_facts,
    waiting_reply,
)
from sqlalchemy import Engine, insert, inspect, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.assessment.contract import (
    ActionNeeded,
    InvalidOutput,
    NoActionNeeded,
    Waiting,
    parse_reply,
)
from app.assessment.grounding import check_grounding
from app.assessment.model_input import canonical_json, fingerprint
from app.assessment.prompt import PROMPT_VERSION
from app.assessment.provider import (
    ProviderEmptyResponse,
    ProviderError,
    ProviderTimeout,
)
from app.assessment.service import (
    RelationshipNotFound,
    Unavailable,
    get_or_create_assessment,
)
from app.db import Assessment, Interaction, create_tables, make_engine
from app.seed import seed_database

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    create_tables(engine)
    store_facts(engine)
    return engine


def stored_rows(engine: Engine) -> list[Assessment]:
    with Session(engine) as session:
        return list(session.scalars(select(Assessment)))


def expected_fingerprint(provider: FakeProvider) -> str:
    return fingerprint(sample_input()[0], provider.name, provider.model)


def grounded_json(reply: dict[str, Any]) -> str:
    """A reply as the lifecycle would store it: checked, with real ids."""
    evidence = sample_input()[1]
    return check_grounding(parse_reply(json.dumps(reply)), evidence).model_dump_json()


async def assess(engine: Engine, provider: FakeProvider, customer_id=RELATIONSHIP_ID):
    return await get_or_create_assessment(engine, provider, customer_id)


# --- schema ---


def test_creating_tables_adds_the_assessment_table(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    create_tables(engine)

    assert "assessments" in inspect(engine).get_table_names()


def test_an_assessment_for_an_unknown_customer_is_rejected(engine: Engine) -> None:
    with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
        session.execute(
            insert(Assessment).values(
                customer_id="cust_missing",
                fingerprint="f",
                result_json="{}",
                provider="fake",
                model="fake-model",
                prompt_version=PROMPT_VERSION,
                created_at=datetime.now(UTC),
            )
        )


def test_reseeding_facts_keeps_stored_assessments(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'seeded.db'}")
    create_tables(engine)
    seed_database(engine)
    row = {
        "customer_id": "cust_001",
        "fingerprint": "abc",
        "result_json": '{"outcome": "insufficient_evidence"}',
        "provider": "fake",
        "model": "fake-model",
        "prompt_version": PROMPT_VERSION,
        "created_at": datetime.now(UTC),
    }
    with Session(engine) as session, session.begin():
        session.execute(insert(Assessment).values(row))

    create_tables(engine)
    seed_database(engine)

    rows = stored_rows(engine)
    assert [(r.customer_id, r.fingerprint) for r in rows] == [("cust_001", "abc")]


# --- stored and reused ---


@pytest.mark.parametrize(
    ("reply", "expected_type"),
    [
        (action_needed_reply(), ActionNeeded),
        (waiting_reply(), Waiting),
        (no_action_needed_reply(), NoActionNeeded),
    ],
)
async def test_valid_assessment_is_stored_once_and_reused(
    engine: Engine, reply: dict[str, Any], expected_type: type
) -> None:
    facts_before = fact_snapshot(engine)
    provider = FakeProvider(reply)

    first = await assess(engine, provider)
    second = await assess(engine, provider)

    assert provider.calls == 1
    assert isinstance(first, expected_type)
    assert second == first
    # Real ids, never handles.
    assert first.reason.evidence[0].startswith("int_")
    [row] = stored_rows(engine)
    assert row.customer_id == RELATIONSHIP_ID
    assert row.fingerprint == expected_fingerprint(provider)
    assert (row.provider, row.model, row.prompt_version) == (
        "fake",
        "fake-model",
        PROMPT_VERSION,
    )
    assert parse_reply(row.result_json) == first
    assert fact_snapshot(engine) == facts_before


async def test_provider_gets_the_canonical_model_input(engine: Engine) -> None:
    provider = FakeProvider(action_needed_reply())

    await assess(engine, provider)

    assert provider.last_input_json == canonical_json(sample_input()[0])


async def test_insufficient_evidence_is_stored_and_reused(engine: Engine) -> None:
    provider = FakeProvider(insufficient_evidence_reply())

    first = await assess(engine, provider)
    second = await assess(engine, provider)

    assert first == second == Unavailable("insufficient_evidence")
    assert not isinstance(first, NoActionNeeded)
    assert provider.calls == 1
    [row] = stored_rows(engine)
    assert json.loads(row.result_json) == {"outcome": "insufficient_evidence"}


def change_note(engine: Engine) -> None:
    with Session(engine) as session, session.begin():
        session.execute(
            update(Interaction)
            .where(Interaction.id == "int_103")
            .values(notes="Sent pricing. They asked for a discount.")
        )


def add_interaction(engine: Engine) -> None:
    with Session(engine) as session, session.begin():
        session.execute(
            insert(Interaction).values(
                id="int_107",
                customer_id=RELATIONSHIP_ID,
                contact_id="contact_101",
                type="call",
                occurred_at=date(2026, 8, 25),
                notes="Asked for a demo.",
            )
        )


@pytest.mark.parametrize("change", [change_note, add_interaction])
async def test_changed_input_is_assessed_again(engine: Engine, change) -> None:
    provider = FakeProvider(insufficient_evidence_reply(), action_needed_reply())
    await assess(engine, provider)
    old_fingerprint = stored_rows(engine)[0].fingerprint

    # The facts are read-only in the product; only this test fixture changes them.
    change(engine)
    result = await assess(engine, provider)

    assert provider.calls == 2
    assert isinstance(result, ActionNeeded)
    fingerprints = {row.fingerprint for row in stored_rows(engine)}
    assert len(fingerprints) == 2
    assert old_fingerprint in fingerprints


# --- failures: nothing stored, next request tries again ---


def grounding_failure(evidence: str) -> dict[str, Any]:
    reply = action_needed_reply()
    reply["next_action"] = claim("Follow up on the pricing.", evidence)
    return reply


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        ("not json {", InvalidOutput),
        ({"outcome": "assessed", "state": "action_needed"}, InvalidOutput),
        (grounding_failure(E_FOREIGN), InvalidOutput),
        (grounding_failure(E_EMPTY_NOTE), InvalidOutput),
        (ProviderTimeout("no reply"), ProviderTimeout),
        (ProviderError("HTTP 503"), ProviderError),
        (ProviderEmptyResponse("request blocked"), ProviderEmptyResponse),
    ],
)
async def test_failure_stores_nothing_and_the_next_request_tries_again(
    engine: Engine, failure: Any, expected: type[Exception]
) -> None:
    facts_before = fact_snapshot(engine)
    provider = FakeProvider(failure, action_needed_reply())

    with pytest.raises(expected):
        await assess(engine, provider)

    assert stored_rows(engine) == []
    assert fact_snapshot(engine) == facts_before
    retried = await assess(engine, provider)
    assert provider.calls == 2
    assert isinstance(retried, ActionNeeded)


async def test_grounding_failure_rejects_the_whole_reply(engine: Engine) -> None:
    # Only next_action is bad; the valid claims are not kept either.
    provider = FakeProvider(grounding_failure(E_FOREIGN))

    with pytest.raises(InvalidOutput) as raised:
        await assess(engine, provider)

    assert (raised.value.check, raised.value.path) == ("G1", "next_action.evidence[0]")
    assert stored_rows(engine) == []


async def test_unexpected_error_is_not_hidden_and_stores_nothing(
    engine: Engine,
) -> None:
    provider = FakeProvider(RuntimeError("Gemini refused the request (HTTP 401)."))

    with pytest.raises(RuntimeError):
        await assess(engine, provider)

    assert stored_rows(engine) == []


# --- decided in code, no model call ---


@pytest.mark.parametrize(
    ("customer_id", "cause"),
    [
        (NO_INTERACTIONS_ID, "no_interactions"),
        (EMPTY_NOTES_ID, "insufficient_evidence"),
    ],
)
async def test_code_decided_cases_make_no_model_call_and_store_nothing(
    engine: Engine, customer_id: str, cause: str
) -> None:
    provider = FakeProvider()

    result = await assess(engine, provider, customer_id)

    assert result == Unavailable(cause)
    assert provider.calls == 0
    assert stored_rows(engine) == []


async def test_unknown_relationship_is_not_found(engine: Engine) -> None:
    provider = FakeProvider()

    with pytest.raises(RelationshipNotFound):
        await assess(engine, provider, "cust_missing")

    assert provider.calls == 0


# --- corrupt stored row ---


@pytest.mark.parametrize(
    "corrupt",
    [
        "not json",
        '{"outcome": "broken"}',
        # Parses as JSON but breaks the state rules.
        json.dumps({**no_action_needed_reply(), "next_action": claim("x", "int_103")}),
    ],
)
async def test_corrupt_stored_row_is_replaced_by_a_new_assessment(
    engine: Engine, corrupt: str
) -> None:
    facts_before = fact_snapshot(engine)
    provider = FakeProvider(action_needed_reply())
    key = expected_fingerprint(provider)
    with Session(engine) as session, session.begin():
        session.execute(
            insert(Assessment).values(
                customer_id=RELATIONSHIP_ID,
                fingerprint=key,
                result_json=corrupt,
                provider="fake",
                model="fake-model",
                prompt_version=PROMPT_VERSION,
                created_at=datetime.now(UTC),
            )
        )

    result = await assess(engine, provider)

    assert provider.calls == 1
    assert isinstance(result, ActionNeeded)
    [row] = stored_rows(engine)
    assert row.fingerprint == key
    assert parse_reply(row.result_json) == result
    assert fact_snapshot(engine) == facts_before


# --- racing requests ---


class RacingProvider(FakeProvider):
    """Another request stores its result while this one waits for the model."""

    def __init__(self, engine: Engine, *replies: Any) -> None:
        super().__init__(*replies)
        self.engine = engine

    async def generate(self, *args: Any) -> str:
        with Session(self.engine) as session, session.begin():
            session.execute(
                insert(Assessment).values(
                    customer_id=RELATIONSHIP_ID,
                    fingerprint=expected_fingerprint(self),
                    result_json=grounded_json(waiting_reply()),
                    provider=self.name,
                    model=self.model,
                    prompt_version=PROMPT_VERSION,
                    created_at=datetime.now(UTC),
                )
            )
        return await super().generate(*args)


async def test_racing_request_returns_the_row_stored_first(engine: Engine) -> None:
    provider = RacingProvider(engine, action_needed_reply())

    result = await assess(engine, provider)

    assert isinstance(result, Waiting)
    [row] = stored_rows(engine)
    assert parse_reply(row.result_json) == result
    assert E_PRICING_SENT not in row.result_json
