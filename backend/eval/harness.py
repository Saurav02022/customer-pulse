"""Run one evaluation case through the production assessment pipeline and record it.

The pipeline is exactly the production one, minus the cache: model-input builder, real
provider, ``parse_reply`` and ``check_grounding``. ``get_or_create_assessment`` and the
assessment table are not used, so no stored row can satisfy a case (AI_EVALUATION.md
section 16; task section 5).

Only mechanical facts are decided here: the outcome, the reliability class, the hard
checks the code already owns (H1-H11), and the H14 same-date order flag. The semantic
dimensions G, C, N and R are left for human review (section 15); this harness never asks
a model to score another model.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.assessment.contract import (
    RESPONSE_SCHEMA,
    Claim,
    InsufficientEvidence,
    InvalidOutput,
    ModelResult,
    parse_reply,
)
from app.assessment.grounding import check_grounding
from app.assessment.model_input import (
    build_model_input,
    canonical_json,
    fingerprint,
)
from app.assessment.prompt import SYSTEM_INSTRUCTION
from app.assessment.provider import (
    AssessmentProvider,
    ProviderEmptyResponse,
    ProviderError,
    ProviderTimeout,
)
from eval.cases import Case

BUSINESS_STATES = {"action_needed", "waiting", "no_action_needed"}

# H14 vocabulary (AI_EVALUATION.md section 4).
_ORDER_WORD = re.compile(
    r"\b(after|before|then|later|earlier|first|last|followed|previously)\b", re.I
)
_LATEST_WORD = re.compile(r"\b(latest|most recent|last)\b", re.I)


@dataclass
class RunRecord:
    case_id: str
    case_type: str
    name: str
    expected_outcome: str
    # Reliability: ok, provider_timeout, provider_error, empty_or_blocked, setup_error.
    reliability: str
    # Structured output: ok, malformed_json, contract.
    structured_output: str = "n/a"
    # Grounding: ok, or a check id G1..G6.
    grounding: str = "n/a"
    actual_outcome: str | None = None  # insufficient_evidence or a state
    state_correct: bool | None = None  # S == 2
    hard_validation: str = "n/a"  # pass, or the first failing check id
    h14_flags: list[dict[str, str]] = field(default_factory=list)
    mechanical_critical: list[str] = field(default_factory=list)
    # The trusted, grounded result with real ids (never raw provider text).
    trusted_result: dict[str, Any] | None = None
    provisional_semantic: dict[str, str] = field(default_factory=dict)
    provider_attempts: int | None = None
    latency_ms: int | None = None
    note: str = ""
    # Formal acceptance: which of the independent runs this result belongs to.
    run: int = 1
    # Human review, filled in after the run. h14_review holds one decision per H14
    # flag ("supported: <why>" or "CF6: <why>"); critical_flags holds confirmed CF
    # codes; semantic holds reviewed G/C/N/R values (0, 1, 2) with a short note.
    h14_review: list[str] = field(default_factory=list)
    critical_flags: list[str] = field(default_factory=list)
    semantic: dict[str, Any] = field(default_factory=dict)


@contextmanager
def _count_provider_calls() -> Iterator[list[str]]:
    """Collect each real provider call line so attempts (including one internal retry)
    can be counted. Harmless for a fake provider, which logs nothing."""
    results: list[str] = []

    class _Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            message = record.getMessage()
            if message.startswith("gemini call"):
                results.append(message)

    logger = logging.getLogger("app.assessment.gemini")
    handler = _Handler()
    # The provider logs each attempt at INFO; capture those even when the app has not
    # configured logging. The lines carry no note text, prompt or reply (gemini._log).
    previous_level = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        yield results
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


def _iter_claims(result: ModelResult) -> Iterator[tuple[str, Claim]]:
    yield "summary", result.summary
    yield "reason", result.reason
    for number, item in enumerate(result.open_items):
        yield f"open_items[{number}]", item
    for name in ("waiting_for", "next_action"):
        claim = getattr(result, name, None)
        if claim is not None:
            yield name, claim


def h14_flags(result: ModelResult, case: Case) -> list[dict[str, str]]:
    """Flag claims that could imply an order the input does not establish.

    A claim is flagged when it cites two or more interactions sharing a date, or says
    latest/most recent/last while the latest date holds more than one interaction, AND
    the text uses an order word. Evidence holds real ids after grounding.
    """
    if isinstance(result, InsufficientEvidence):
        return []
    date_of: dict[str, date] = {i.id: i.occurred_at for i in case.interactions}
    if not date_of:
        return []
    latest_date = max(date_of.values())
    latest_has_many = sum(1 for d in date_of.values() if d == latest_date) > 1

    flags: list[dict[str, str]] = []
    for path, claim in _iter_claims(result):
        cited_dates = [date_of[e] for e in claim.evidence if e in date_of]
        cites_same_date = len(cited_dates) != len(set(cited_dates))
        latest_mention = latest_has_many and bool(_LATEST_WORD.search(claim.text))
        order = _ORDER_WORD.findall(claim.text)
        if (cites_same_date or latest_mention) and order:
            flags.append(
                {
                    "path": path,
                    "order_words": ",".join(sorted({w.lower() for w in order})),
                    "text": claim.text,
                }
            )
    return flags


def _score_state(expected: str, actual: str) -> tuple[bool, list[str]]:
    """S and any mechanical critical failure that the plan makes certain."""
    correct = actual == expected
    critical: list[str] = []
    # A business state on a decline-only case is CF2 by the plan (sections 7, 9).
    decline_only = expected == "insufficient_evidence"
    if decline_only and actual in BUSINESS_STATES:
        critical.append("CF2")
    return correct, critical


async def run_case(provider: AssessmentProvider, case: Case) -> RunRecord:
    """One model call for one case, then the production validation. No cache, no DB."""
    record = RunRecord(
        case_id=case.case_id,
        case_type=case.case_type,
        name=case.name,
        expected_outcome=case.expected_outcome,
        reliability="ok",
        note=case.note,
    )
    model_input, evidence = build_model_input(
        case.status, case.contacts, case.interactions
    )
    input_json = canonical_json(model_input)
    # Recorded for traceability; never used to read or write a stored assessment.
    _ = fingerprint(model_input, provider.name, provider.model)

    started = time.monotonic()
    with _count_provider_calls() as calls:
        try:
            raw = await provider.generate(
                SYSTEM_INSTRUCTION, input_json, RESPONSE_SCHEMA
            )
        except ProviderTimeout:
            record.reliability = "provider_timeout"
        except ProviderError:
            record.reliability = "provider_error"
        except ProviderEmptyResponse:
            record.reliability = "empty_or_blocked"
        except RuntimeError:
            # A request the API refuses as wrong (bad key/model). Never a state.
            record.reliability = "setup_error"
        else:
            record.reliability = "ok"
    record.latency_ms = int((time.monotonic() - started) * 1000)
    record.provider_attempts = len(calls) or None

    if record.reliability != "ok":
        return record

    try:
        parsed = parse_reply(raw)
    except InvalidOutput as error:
        record.structured_output = (
            "malformed_json" if error.check == "json" else "contract"
        )
        record.hard_validation = error.check + (f":{error.path}" if error.path else "")
        return record
    record.structured_output = "ok"

    try:
        grounded = check_grounding(parsed, evidence)
    except InvalidOutput as error:
        record.grounding = error.check
        record.hard_validation = (
            f"{error.check}:{error.path}" if error.path else error.check
        )
        return record
    record.grounding = "ok"
    record.hard_validation = "pass"

    outcome = (
        "insufficient_evidence"
        if isinstance(grounded, InsufficientEvidence)
        else grounded.state
    )
    record.actual_outcome = outcome
    record.state_correct, record.mechanical_critical = _score_state(
        case.expected_outcome, outcome
    )
    record.trusted_result = grounded.model_dump()
    record.h14_flags = h14_flags(grounded, case)
    record.provisional_semantic = {
        dim: "pending_human_review" for dim in ("G", "C", "N", "R")
    }
    return record


# --- aggregation ----------------------------------------------------------------------

TRANSIENT = {"provider_timeout", "provider_error"}


def aggregate(records: list[RunRecord]) -> dict[str, Any]:
    """Counts the report needs; no averaging that could hide a single failure."""
    completed = [r for r in records if r.reliability not in TRANSIENT]
    transient = [r for r in records if r.reliability in TRANSIENT]
    trusted = [r for r in completed if r.hard_validation == "pass"]
    structured_failures = [
        r for r in completed if r.structured_output in {"malformed_json", "contract"}
    ]
    empty_blocked = [r for r in completed if r.reliability == "empty_or_blocked"]
    grounding_failures = [r for r in completed if r.grounding not in {"ok", "n/a"}]
    critical = [(r.case_id, code) for r in records for code in r.mechanical_critical]
    h14 = [(r.case_id, len(r.h14_flags)) for r in records if r.h14_flags]

    seeded = [r for r in trusted if r.case_type == "seeded"]
    synthetic = [r for r in trusted if r.case_type == "synthetic"]
    return {
        "cases": len(records),
        "completed_results": len(completed),
        "transient_failures": len(transient),
        "transient_by_cause": _by(transient, lambda r: r.reliability),
        "trusted_results": len(trusted),
        "structured_output_failures": len(structured_failures),
        "empty_or_blocked": len(empty_blocked),
        "grounding_failures": len(grounding_failures),
        "mechanical_critical_failures": critical,
        "h14_flagged_cases": h14,
        "seeded_state_correct": sum(1 for r in seeded if r.state_correct),
        "seeded_total": sum(1 for r in records if r.case_type == "seeded"),
        "synthetic_state_correct": sum(1 for r in synthetic if r.state_correct),
        "synthetic_total": sum(1 for r in records if r.case_type == "synthetic"),
    }


def _by(records: list[RunRecord], key: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in records:
        out[key(r)] = out.get(key(r), 0) + 1
    return out
