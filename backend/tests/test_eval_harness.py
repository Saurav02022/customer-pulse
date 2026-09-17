"""Offline tests for the evaluation harness. No real model is ever called: every case
runs through the production pipeline with FakeProvider scripted replies.
"""

import json
from datetime import date

import pytest

from app.assessment.model_input import handle
from eval.cases import (
    EVAL_SET_VERSION,
    SEEDED_EXPECTED,
    Case,
    EvalContact,
    EvalInteraction,
    _reversed_within_date_ids,
    load_cases,
    seeded_facts,
)
from eval.harness import aggregate, run_case
from eval.report import (
    ALLOWED_META_FIELDS,
    ALLOWED_RECORD_FIELDS,
    run_metadata,
    to_json,
    to_markdown,
)
from tests.assessment_support import FakeProvider

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# --- small controlled cases -----------------------------------------------------------

CONTACT = EvalContact("t_contact", "Test Owner", "Owner")
E_A = handle("e_", "t_int_a")
E_B = handle("e_", "t_int_b")
C = handle("c_", "t_contact")


def _pricing_case(expected: str = "action_needed") -> Case:
    return Case(
        "T-1",
        "synthetic",
        "controlled case",
        "prospect",
        [CONTACT],
        [
            EvalInteraction(
                "t_int_a",
                "t_contact",
                "email",
                date(2026, 5, 1),
                "Asked about pricing.",
            ),
            EvalInteraction(
                "t_int_b", "t_contact", "note", date(2026, 5, 3), "No reply yet."
            ),
        ],
        expected,
        "controlled",
    )


def _action_needed_reply(reason: str = "No reply after the pricing question.") -> dict:
    return {
        "outcome": "assessed",
        "state": "action_needed",
        "summary": {"text": "Pricing asked and no reply.", "evidence": [E_A, E_B]},
        "reason": {"text": reason, "evidence": [E_B]},
        "open_items": [
            {"text": "Follow up on pricing.", "evidence": [E_B], "contacts": [C]}
        ],
        "next_action": {"text": "Follow up with the owner.", "evidence": [E_B]},
    }


# --- case loading ---------------------------------------------------------------------


def test_load_cases_has_the_approved_22() -> None:
    cases = load_cases()
    assert len(cases) == 22
    assert sum(1 for c in cases if c.case_type == "seeded") == 12
    assert sum(1 for c in cases if c.case_type == "synthetic") == 10
    ids = {c.case_id for c in cases}
    assert {f"cust_{n:03d}" for n in range(1, 13)} <= ids
    assert {
        "INJ-1",
        "INJ-2",
        "INJ-3",
        "INJ-4",
        "IE-3",
        "IE-4",
        "IE-5",
        "CHR-1",
        "D-1",
        "MC-1",
    } <= ids


def test_seeded_expected_distribution_matches_the_plan() -> None:
    values = list(SEEDED_EXPECTED.values())
    assert values.count("action_needed") == 6
    assert values.count("waiting") == 3
    assert values.count("no_action_needed") == 3


# --- one case through the pipeline ----------------------------------------------------


async def test_trusted_valid_result_is_scored() -> None:
    provider = FakeProvider(_action_needed_reply())
    record = await run_case(provider, _pricing_case())
    assert record.reliability == "ok"
    assert record.structured_output == "ok"
    assert record.grounding == "ok"
    assert record.hard_validation == "pass"
    assert record.actual_outcome == "action_needed"
    assert record.state_correct is True
    # Grounding maps handles back to the real ids.
    assert record.trusted_result["reason"]["evidence"] == ["t_int_b"]


async def test_provider_timeout_is_a_reliability_outcome() -> None:
    from app.assessment.provider import ProviderTimeout

    provider = FakeProvider(ProviderTimeout("no reply"))
    record = await run_case(provider, _pricing_case())
    assert record.reliability == "provider_timeout"
    assert record.trusted_result is None
    assert record.actual_outcome is None


async def test_malformed_json_is_a_structured_failure() -> None:
    provider = FakeProvider("this is not json")
    record = await run_case(provider, _pricing_case())
    assert record.reliability == "ok"
    assert record.structured_output == "malformed_json"
    assert record.hard_validation.startswith("json")
    assert record.trusted_result is None


async def test_unknown_handle_is_a_grounding_failure() -> None:
    reply = _action_needed_reply()
    reply["reason"]["evidence"] = ["e_unknownhandle"]
    provider = FakeProvider(reply)
    record = await run_case(provider, _pricing_case())
    assert record.structured_output == "ok"
    assert record.grounding == "G1"
    assert record.trusted_result is None


async def test_business_state_on_a_decline_case_is_cf2() -> None:
    inj4 = next(c for c in load_cases() if c.case_id == "INJ-4")
    e = handle("e_", "inj4_note")
    c = handle("c_", "contact_i4")
    reply = {
        "outcome": "assessed",
        "state": "action_needed",
        "summary": {"text": "Record needs action.", "evidence": [e]},
        "reason": {"text": "There is a request to handle.", "evidence": [e]},
        "open_items": [{"text": "Do the thing.", "evidence": [e], "contacts": [c]}],
        "next_action": {"text": "Reply to the contact.", "evidence": [e]},
    }
    record = await run_case(FakeProvider(reply), inj4)
    assert record.actual_outcome == "action_needed"
    assert record.state_correct is False
    assert "CF2" in record.mechanical_critical


# --- H14 same-date order flag ---------------------------------------------------------


def _same_date_case() -> Case:
    return Case(
        "T-2",
        "synthetic",
        "same-date",
        "prospect",
        [CONTACT],
        [
            EvalInteraction(
                "t_x", "t_contact", "email", date(2026, 5, 1), "Pricing asked."
            ),
            EvalInteraction("t_y", "t_contact", "note", date(2026, 5, 1), "No reply."),
        ],
        "action_needed",
        "same-date",
    )


async def test_h14_flags_same_date_claim_with_order_word() -> None:
    ex, ey = handle("e_", "t_x"), handle("e_", "t_y")
    reply = {
        "outcome": "assessed",
        "state": "action_needed",
        "summary": {
            "text": "Pricing was asked and no reply came.",
            "evidence": [ex, ey],
        },
        "reason": {
            "text": "No reply came after the pricing email.",
            "evidence": [ex, ey],
        },
        "open_items": [{"text": "Follow up.", "evidence": [ey], "contacts": [C]}],
        "next_action": {"text": "Follow up with the owner.", "evidence": [ey]},
    }
    record = await run_case(FakeProvider(reply), _same_date_case())
    assert record.grounding == "ok"
    flagged = {f["path"] for f in record.h14_flags}
    assert "reason" in flagged  # cites both same-date ids and uses "after"
    assert "summary" not in flagged  # cites both but has no order word


# --- aggregation ----------------------------------------------------------------------


async def test_aggregate_counts_reliability_and_state() -> None:
    from app.assessment.provider import ProviderError

    ok = await run_case(FakeProvider(_action_needed_reply()), _pricing_case())
    timeout = await run_case(FakeProvider(ProviderError("5xx")), _pricing_case())
    agg = aggregate([ok, timeout])
    assert agg["cases"] == 2
    assert agg["completed_results"] == 1
    assert agg["transient_failures"] == 1
    assert agg["trusted_results"] == 1
    assert agg["transient_by_cause"] == {"provider_error": 1}


# --- serialization has no secrets -----------------------------------------------------


async def test_artifacts_carry_no_secret_fields() -> None:
    provider = FakeProvider(_action_needed_reply())
    record = await run_case(provider, _pricing_case())
    meta = run_metadata(provider)
    assert set(meta) <= ALLOWED_META_FIELDS
    assert meta["eval_set_version"] == EVAL_SET_VERSION

    payload = to_json(meta, [record])
    for stored in payload["records"]:
        assert set(stored) == ALLOWED_RECORD_FIELDS
    dumped = json.dumps(payload)
    lowered = dumped.lower()
    for banned in ("api_key", "secret", "gemini_api_key", "token", "secretstr", ".env"):
        assert banned not in lowered
    # Markdown summary is also secret-free and renders.
    assert "baseline" in to_markdown(meta, [record]).lower()


# --- CHR-1 order reversal -------------------------------------------------------------


def test_chr1_reverses_within_date_handle_order() -> None:
    _, original = seeded_facts("cust_009")
    reversed_ids = _reversed_within_date_ids(original)

    def fact_key(i: EvalInteraction) -> tuple[str, str, str, str]:
        return (i.occurred_at.isoformat(), i.type, i.contact_id, i.notes)

    # Facts and dates are unchanged; only the ids (hence handles) move.
    assert {fact_key(i) for i in original} == {fact_key(i) for i in reversed_ids}

    def by_date(interactions: list[EvalInteraction]) -> dict:
        out: dict = {}
        for i in interactions:
            out.setdefault(i.occurred_at, []).append(i)
        return out

    original_by_date = by_date(original)
    reversed_by_date = by_date(reversed_ids)
    shared = [d for d, group in original_by_date.items() if len(group) > 1]
    assert shared  # cust_009 has same-date pairs
    for day in shared:
        orig_order = [
            fact_key(i)
            for i in sorted(original_by_date[day], key=lambda x: handle("e_", x.id))
        ]
        rev_order = [
            fact_key(i)
            for i in sorted(reversed_by_date[day], key=lambda x: handle("e_", x.id))
        ]
        assert rev_order == list(reversed(orig_order))
