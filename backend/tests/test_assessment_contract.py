"""AI assessment contract: which replies parse and which impossible ones fail."""

import json
from collections.abc import Callable
from typing import Any

import pytest
from assessment_support import (
    action_needed_reply,
    claim,
    insufficient_evidence_reply,
    no_action_needed_reply,
    open_item,
    waiting_reply,
)

from app.assessment.contract import (
    ActionNeeded,
    InsufficientEvidence,
    InvalidOutput,
    NoActionNeeded,
    Waiting,
    parse_reply,
)

Reply = dict[str, Any]


def parse(reply: Reply):
    return parse_reply(json.dumps(reply))


@pytest.mark.parametrize(
    ("build", "expected"),
    [
        (action_needed_reply, ActionNeeded),
        (waiting_reply, Waiting),
        (no_action_needed_reply, NoActionNeeded),
        (insufficient_evidence_reply, InsufficientEvidence),
    ],
)
def test_each_valid_outcome_parses(build: Callable[[], Reply], expected: type) -> None:
    assert type(parse(build())) is expected


def test_waiting_may_carry_a_next_action() -> None:
    reply = waiting_reply() | {"next_action": claim("Call after the plan.", "e_x")}
    result = parse(reply)
    assert isinstance(result, Waiting)
    assert result.next_action is not None


def test_nulls_from_the_flat_schema_mean_not_given() -> None:
    # The model gets one flat schema with every field nullable.
    flat_nulls = {"waiting_for": None, "next_action": None, "state": None}
    flat_nulls |= {"summary": None, "reason": None, "open_items": None}
    assert isinstance(
        parse(insufficient_evidence_reply() | flat_nulls), InsufficientEvidence
    )
    assert isinstance(
        parse(no_action_needed_reply() | {"waiting_for": None, "next_action": None}),
        NoActionNeeded,
    )
    assert isinstance(
        parse(action_needed_reply() | {"waiting_for": None}), ActionNeeded
    )


def without(reply: Reply, field: str) -> Reply:
    return {key: value for key, value in reply.items() if key != field}


def with_summary(**changes: Any) -> Reply:
    reply = action_needed_reply()
    reply["summary"] = reply["summary"] | changes
    return reply


REJECTED = {
    "no action needed with a next action": no_action_needed_reply()
    | {"next_action": claim("Check in.", "e_x")},
    "no action needed with open items": no_action_needed_reply()
    | {"open_items": [open_item("Check in.", ["e_x"], ["c_x"])]},
    "no action needed with waiting_for": no_action_needed_reply()
    | {"waiting_for": claim("A meeting.", "e_x")},
    "waiting without waiting_for": without(waiting_reply(), "waiting_for"),
    "waiting with null waiting_for": waiting_reply() | {"waiting_for": None},
    "action needed without next action": without(action_needed_reply(), "next_action"),
    "action needed with null next action": action_needed_reply()
    | {"next_action": None},
    "action needed with waiting_for": action_needed_reply()
    | {"waiting_for": claim("A meeting.", "e_x")},
    "action needed without open_items": without(action_needed_reply(), "open_items"),
    "unknown field": action_needed_reply() | {"confidence": 0.9},
    "unknown field inside a claim": with_summary(confidence=0.9),
    "unavailable is not a state": action_needed_reply() | {"state": "unavailable"},
    "assessed without a state": without(action_needed_reply(), "state"),
    "unknown outcome": action_needed_reply() | {"outcome": "error"},
    "missing outcome": without(action_needed_reply(), "outcome"),
    "insufficient evidence with a state": insufficient_evidence_reply()
    | {"state": "no_action_needed"},
    "insufficient evidence with a summary": insufficient_evidence_reply()
    | {"summary": claim("Not much here.", "e_x")},
    "claim without evidence": with_summary(evidence=None),
    "claim with empty evidence": with_summary(evidence=[]),
    "claim with a null handle": with_summary(evidence=[None]),
    "claim with blank text": with_summary(text="   "),
    "claim with a non-text value": with_summary(text=42),
    "open item without contacts": action_needed_reply()
    | {"open_items": [open_item("Reply.", ["e_x"], [])]},
    "summary missing": without(action_needed_reply(), "summary"),
    "reason missing": without(action_needed_reply(), "reason"),
}


@pytest.mark.parametrize("reply", REJECTED.values(), ids=REJECTED.keys())
def test_impossible_replies_are_rejected_as_contract_failures(reply: Reply) -> None:
    with pytest.raises(InvalidOutput) as error:
        parse(reply)
    assert error.value.check == "contract"


@pytest.mark.parametrize("raw", ["", "not json", "{", '{"outcome": "assessed"'])
def test_text_that_is_not_json_is_a_json_failure(raw: str) -> None:
    with pytest.raises(InvalidOutput) as error:
        parse_reply(raw)
    assert error.value.check == "json"


@pytest.mark.parametrize("raw", ["[]", "null", '"action_needed"', "3"])
def test_json_that_is_not_an_object_is_a_contract_failure(raw: str) -> None:
    with pytest.raises(InvalidOutput) as error:
        parse_reply(raw)
    assert error.value.check == "contract"


def test_failure_names_the_field_but_never_carries_reply_text() -> None:
    reply = action_needed_reply()
    reply["open_items"][0]["evidence"] = "SECRET NOTE TEXT"
    with pytest.raises(InvalidOutput) as error:
        parse(reply)
    assert "open_items[0].evidence" in error.value.path
    assert "SECRET" not in str(error.value)
    # The chained pydantic error would quote the reply, so it is dropped.
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__
