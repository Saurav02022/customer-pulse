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
    RESPONSE_SCHEMA,
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


# --- the flat schema sent to the model ---

# Keywords Gemini's response_json_schema accepts (google-genai 2.23.0), minus the ones
# we never send ($defs, $ref and friends: the schema is inlined).
SUPPORTED_KEYWORDS = {
    "type",
    "format",
    "enum",
    "items",
    "prefixItems",
    "minItems",
    "maxItems",
    "minimum",
    "maximum",
    "anyOf",
    "properties",
    "additionalProperties",
    "required",
}


def keywords(node: Any) -> set[str]:
    if isinstance(node, list):
        return set().union(*(keywords(item) for item in node))
    if not isinstance(node, dict):
        return set()
    found = set(node)
    for key, value in node.items():
        # Under "properties" the keys are field names, not keywords.
        children = value.values() if key == "properties" else [value]
        found |= set().union(*(keywords(child) for child in children))
    return found


def conforms(value: Any, schema: dict[str, Any]) -> bool:
    """A small check for the keywords the schema uses. Enough to show that a reply
    shaped by the schema is one parse_reply() can accept."""
    if "anyOf" in schema:
        return any(conforms(value, option) for option in schema["anyOf"])
    kind = schema["type"]
    if kind == "null":
        return value is None
    if kind == "string":
        return isinstance(value, str) and value in schema.get("enum", [value])
    if kind == "array":
        return (
            isinstance(value, list)
            and len(value) >= schema.get("minItems", 0)
            and all(conforms(item, schema["items"]) for item in value)
        )
    assert kind == "object"
    properties = schema["properties"]
    return (
        isinstance(value, dict)
        and set(schema["required"]) <= set(value)
        and (schema.get("additionalProperties", True) or set(value) <= set(properties))
        and all(conforms(value[key], properties[key]) for key in value)
    )


def as_sent_by_model(reply: Reply) -> Reply:
    # The schema requires every field, so the model sends null for those not used.
    return {name: None for name in RESPONSE_SCHEMA["properties"]} | reply


def test_schema_is_plain_json() -> None:
    assert json.loads(json.dumps(RESPONSE_SCHEMA)) == RESPONSE_SCHEMA


def test_schema_uses_only_keywords_the_provider_supports() -> None:
    # "const", "pattern", "$ref" and "default" from the Pydantic schema are gone.
    assert keywords(RESPONSE_SCHEMA) <= SUPPORTED_KEYWORDS


def test_schema_is_flat_with_only_contract_fields() -> None:
    properties = RESPONSE_SCHEMA["properties"]
    assert set(properties) == {
        "outcome",
        "state",
        "summary",
        "reason",
        "open_items",
        "waiting_for",
        "next_action",
    }
    assert "confidence" not in json.dumps(RESPONSE_SCHEMA)
    assert set(RESPONSE_SCHEMA["required"]) == set(properties)
    assert RESPONSE_SCHEMA["additionalProperties"] is False


def test_schema_offers_the_three_states_and_the_decline() -> None:
    properties = RESPONSE_SCHEMA["properties"]
    assert properties["outcome"] == {
        "type": "string",
        "enum": ["insufficient_evidence", "assessed"],
    }
    state, null = properties["state"]["anyOf"]
    assert state["enum"] == ["action_needed", "waiting", "no_action_needed"]
    assert null == {"type": "null"}


def test_every_field_but_outcome_may_be_null() -> None:
    for name, field in RESPONSE_SCHEMA["properties"].items():
        assert conforms(None, field) == (name != "outcome"), name


def test_schema_keeps_evidence_and_contacts_required_and_non_empty() -> None:
    properties = RESPONSE_SCHEMA["properties"]
    claim = properties["summary"]["anyOf"][0]
    item = properties["open_items"]["anyOf"][0]["items"]
    assert claim["required"] == ["text", "evidence"]
    assert item["required"] == ["text", "evidence", "contacts"]
    assert claim["properties"]["evidence"]["minItems"] == 1
    assert item["properties"]["contacts"]["minItems"] == 1
    assert not conforms({"text": "Sent.", "evidence": []}, claim)
    assert not conforms({"text": "Sent.", "evidence": ["e_x"], "extra": 1}, claim)


@pytest.mark.parametrize(
    "build",
    [
        action_needed_reply,
        waiting_reply,
        no_action_needed_reply,
        insufficient_evidence_reply,
    ],
)
def test_replies_shaped_by_the_schema_parse(build: Callable[[], Reply]) -> None:
    reply = as_sent_by_model(build())
    assert conforms(reply, RESPONSE_SCHEMA)
    parse(reply)


def test_schema_alone_does_not_enforce_state_rules() -> None:
    # The flat schema allows this; the contract rejects it. That is why parse_reply()
    # stays the boundary whatever the provider enforces.
    reply = as_sent_by_model(no_action_needed_reply())
    reply["next_action"] = claim("Check in.", "e_x")
    assert conforms(reply, RESPONSE_SCHEMA)
    with pytest.raises(InvalidOutput):
        parse(reply)
