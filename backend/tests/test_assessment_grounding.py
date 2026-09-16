"""Grounding checks G1 to G6: every claim cites real, non-empty notes of this
relationship, and any failure rejects the whole reply."""

import json
from collections.abc import Callable
from typing import Any

import pytest
from assessment_support import (
    C_FOREIGN,
    C_MANAGER,
    C_OWNER,
    E_EMPTY_NOTE,
    E_FOREIGN,
    E_MANAGER_CALL,
    E_PRICING_ASKED,
    E_PRICING_SENT,
    OTHER_CONTACT,
    OTHER_INTERACTION,
    action_needed_reply,
    claim,
    insufficient_evidence_reply,
    no_action_needed_reply,
    open_item,
    sample_input,
    waiting_reply,
)

from app.assessment.contract import (
    ActionNeeded,
    Claim,
    InsufficientEvidence,
    InvalidOutput,
    NoActionNeeded,
    Waiting,
    parse_reply,
)
from app.assessment.grounding import check_grounding
from app.assessment.model_input import build_model_input

Reply = dict[str, Any]


def ground(reply: Reply):
    _, evidence = sample_input()
    return check_grounding(parse_reply(json.dumps(reply)), evidence)


def rejected(reply: Reply) -> InvalidOutput:
    with pytest.raises(InvalidOutput) as error:
        ground(reply)
    return error.value


# --- valid results ---


def test_valid_action_needed_comes_back_with_real_ids() -> None:
    result = ground(action_needed_reply())
    assert isinstance(result, ActionNeeded)
    assert result.summary.evidence == ["int_101", "int_103"]
    assert result.reason.evidence == ["int_103"]
    assert result.open_items[0].evidence == ["int_103"]
    assert result.open_items[0].contacts == ["contact_101"]
    assert result.next_action.evidence == ["int_103"]
    assert result.next_action.text == "Follow up with Asha on the pricing."


def test_valid_waiting_comes_back_with_real_ids() -> None:
    reply = waiting_reply() | {
        "next_action": claim("Send the plan once decided.", E_MANAGER_CALL)
    }
    result = ground(reply)
    assert isinstance(result, Waiting)
    assert result.waiting_for.evidence == ["int_102"]
    assert result.next_action is not None
    assert result.next_action.evidence == ["int_102"]


def test_valid_no_action_needed_comes_back_with_real_ids() -> None:
    result = ground(no_action_needed_reply())
    assert isinstance(result, NoActionNeeded)
    assert result.open_items == []
    assert result.reason.evidence == ["int_103"]


def test_insufficient_evidence_passes_through_unchanged() -> None:
    result = ground(insufficient_evidence_reply())
    assert result == InsufficientEvidence(outcome="insufficient_evidence")


def test_duplicate_handles_are_removed_in_model_order() -> None:
    reply = action_needed_reply()
    reply["reason"]["evidence"] = [E_PRICING_SENT, E_PRICING_ASKED, E_PRICING_SENT]
    reply["open_items"][0]["contacts"] = [C_OWNER, C_OWNER]
    result = ground(reply)
    assert result.reason.evidence == ["int_103", "int_101"]
    assert result.open_items[0].contacts == ["contact_101"]


def test_open_item_may_name_every_contact_it_cites() -> None:
    reply = action_needed_reply()
    reply["open_items"] = [
        open_item(
            "Agree timing.", [E_PRICING_SENT, E_MANAGER_CALL], [C_MANAGER, C_OWNER]
        )
    ]
    assert ground(reply).open_items[0].contacts == ["contact_102", "contact_101"]


# --- failures ---


def set_evidence(field: str, *handles: str) -> Callable[[], Reply]:
    def build() -> Reply:
        reply = action_needed_reply() if field != "waiting_for" else waiting_reply()
        reply[field]["evidence"] = list(handles)
        return reply

    return build


FAILURES = {
    # G1: the handle must be in this request's map.
    "invented handle in summary": (set_evidence("summary", "e_0000000000"), "G1"),
    "invented handle in reason": (set_evidence("reason", "made-up"), "G1"),
    "invalid handle in next action": (
        set_evidence("next_action", E_PRICING_SENT, "e_ffffffffff"),
        "G1",
    ),
    "invalid handle in waiting_for": (
        set_evidence("waiting_for", "e_1234567890"),
        "G1",
    ),
    "handle of another relationship": (set_evidence("summary", E_FOREIGN), "G1"),
    "real interaction id instead of a handle": (
        set_evidence("reason", "int_103"),
        "G1",
    ),
    "contact handle used as evidence": (set_evidence("reason", C_OWNER), "G1"),
    # G2: empty notes cannot support anything.
    "citation of an empty note": (set_evidence("next_action", E_EMPTY_NOTE), "G2"),
    "empty note in waiting_for": (set_evidence("waiting_for", E_EMPTY_NOTE), "G2"),
}


@pytest.mark.parametrize(("build", "check"), FAILURES.values(), ids=FAILURES.keys())
def test_bad_evidence_is_rejected(build: Callable[[], Reply], check: str) -> None:
    assert rejected(build()).check == check


def test_no_action_needed_resting_only_on_an_empty_note_is_rejected() -> None:
    # Absence of evidence never validates as No action needed.
    reply = no_action_needed_reply()
    reply["summary"]["evidence"] = [E_EMPTY_NOTE]
    reply["reason"]["evidence"] = [E_EMPTY_NOTE]
    assert rejected(reply).check == "G2"


def test_claim_left_without_evidence_is_rejected() -> None:
    # The contract already blocks this; G3 still holds if a result skips parsing.
    result = parse_reply(json.dumps(action_needed_reply()))
    empty = Claim.model_construct(text="Pricing was sent.", evidence=[])
    _, evidence = sample_input()
    with pytest.raises(InvalidOutput) as error:
        check_grounding(result.model_copy(update={"summary": empty}), evidence)
    assert (error.value.check, error.value.path) == ("G3", "summary.evidence")


def with_open_item_contacts(*contacts: str) -> Reply:
    reply = action_needed_reply()
    reply["open_items"][0]["contacts"] = list(contacts)
    return reply


def test_unknown_open_item_contact_is_rejected() -> None:
    error = rejected(with_open_item_contacts(C_OWNER, "c_0000000000"))
    assert (error.check, error.path) == ("G4", "open_items[0].contacts[1]")


def test_contact_of_another_relationship_is_rejected() -> None:
    assert rejected(with_open_item_contacts(C_FOREIGN)).check == "G4"


def test_open_item_contact_must_be_on_a_cited_interaction() -> None:
    # The manager is a real contact here, but the cited note is the owner's.
    assert rejected(with_open_item_contacts(C_MANAGER)).check == "G4"


@pytest.mark.parametrize(
    "text",
    [
        f"See {E_PRICING_SENT} for details.",
        f"See {E_PRICING_SENT.upper()} for details.",
        f"Asha is {C_OWNER}.",
        "Based on int_103.",
        "Owner is contact_101.",
        "Record cust_101 needs a reply.",
    ],
)
def test_text_with_an_id_or_handle_is_rejected(text: str) -> None:
    reply = action_needed_reply()
    reply["next_action"]["text"] = text
    error = rejected(reply)
    assert (error.check, error.path) == ("G5", "next_action.text")


def test_reason_length_limit() -> None:
    reply = action_needed_reply()
    reply["reason"]["text"] = "a" * 200
    assert isinstance(ground(reply), ActionNeeded)
    reply["reason"]["text"] = "a" * 201
    assert (rejected(reply).check, rejected(reply).path) == ("G6", "reason.text")


def test_other_claim_length_limit() -> None:
    reply = action_needed_reply()
    reply["summary"]["text"] = "a" * 300
    assert isinstance(ground(reply), ActionNeeded)
    reply["summary"]["text"] = "a" * 301
    assert rejected(reply).check == "G6"
    reply = action_needed_reply()
    reply["open_items"][0]["text"] = "a" * 301
    assert rejected(reply).path == "open_items[0].text"


# --- whole-result rejection ---


def test_one_bad_citation_rejects_an_otherwise_valid_result() -> None:
    reply = action_needed_reply()
    reply["open_items"].append(
        open_item("Confirm timing.", [E_MANAGER_CALL, E_FOREIGN], [C_MANAGER])
    )
    returned = []
    with pytest.raises(InvalidOutput) as error:
        returned.append(ground(reply))
    assert (error.value.check, error.value.path) == ("G1", "open_items[1].evidence[1]")
    assert returned == []


def test_handle_from_another_relationship_input_does_not_resolve() -> None:
    other_data, _ = build_model_input("customer", [OTHER_CONTACT], [OTHER_INTERACTION])
    [other_handle] = [
        i["handle"] for g in other_data["interaction_dates"] for i in g["interactions"]
    ]
    reply = action_needed_reply()
    reply["reason"]["evidence"] = [other_handle]
    assert rejected(reply).check == "G1"
