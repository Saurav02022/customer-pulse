"""Shared test support for the assessment boundary: a small synthetic relationship,
valid reply builders, and a fake provider. Nothing here calls a real model."""

import json
from datetime import date
from typing import Any

from app.assessment.model_input import EvidenceMap, build_model_input, handle
from app.db import Contact, Interaction

OWNER = Contact(
    id="contact_101",
    customer_id="cust_101",
    name="Asha Rao",
    email="asha@example.test",
    role="Owner",
)
MANAGER = Contact(
    id="contact_102",
    customer_id="cust_101",
    name="Ravi Menon",
    email="ravi@example.test",
    role="Office Manager",
)


def interaction(
    id: str, occurred_at: date, notes: str, contact: Contact = OWNER, type="note"
) -> Interaction:
    return Interaction(
        id=id,
        customer_id=contact.customer_id,
        contact_id=contact.id,
        type=type,
        occurred_at=occurred_at,
        notes=notes,
    )


# int_102 and int_103 share a date. Their handles sort in the opposite order to their
# ids, which the model-input tests rely on.
INTERACTIONS = [
    interaction("int_101", date(2026, 8, 18), "Asked for pricing.", type="email"),
    interaction(
        "int_102",
        date(2026, 8, 20),
        "Wants it before the busy season.",
        MANAGER,
        "call",
    ),
    interaction("int_103", date(2026, 8, 20), "Sent pricing. No response yet."),
    interaction("int_104", date(2026, 8, 21), ""),
]

E_PRICING_ASKED = handle("e_", "int_101")
E_MANAGER_CALL = handle("e_", "int_102")
E_PRICING_SENT = handle("e_", "int_103")
E_EMPTY_NOTE = handle("e_", "int_104")
C_OWNER = handle("c_", "contact_101")
C_MANAGER = handle("c_", "contact_102")

# Records of another relationship.
OTHER_CONTACT = Contact(
    id="contact_901",
    customer_id="cust_901",
    name="Meera Iyer",
    email="meera@example.test",
    role="Owner",
)
OTHER_INTERACTION = interaction(
    "int_901", date(2026, 8, 20), "Asked about SMS support.", OTHER_CONTACT
)
E_FOREIGN = handle("e_", "int_901")
C_FOREIGN = handle("c_", "contact_901")


def sample_input() -> tuple[dict[str, Any], EvidenceMap]:
    return build_model_input("prospect", [OWNER, MANAGER], INTERACTIONS)


def claim(text: str, *evidence: str) -> dict[str, Any]:
    return {"text": text, "evidence": list(evidence)}


def open_item(text: str, evidence: list[str], contacts: list[str]) -> dict[str, Any]:
    return {"text": text, "evidence": evidence, "contacts": contacts}


def action_needed_reply() -> dict[str, Any]:
    return {
        "outcome": "assessed",
        "state": "action_needed",
        "summary": claim(
            "Pricing was asked for and sent.", E_PRICING_ASKED, E_PRICING_SENT
        ),
        "reason": claim(
            "Pricing was sent and no response is recorded.", E_PRICING_SENT
        ),
        "open_items": [
            open_item("Get a reply on the pricing.", [E_PRICING_SENT], [C_OWNER])
        ],
        "next_action": claim("Follow up with Asha on the pricing.", E_PRICING_SENT),
    }


def waiting_reply() -> dict[str, Any]:
    return {
        "outcome": "assessed",
        "state": "waiting",
        "summary": claim("Pricing was sent.", E_PRICING_SENT),
        "reason": claim("Waiting for the busy season plan.", E_MANAGER_CALL),
        "open_items": [],
        "waiting_for": claim("The busy season plan.", E_MANAGER_CALL),
        "next_action": None,
    }


def no_action_needed_reply() -> dict[str, Any]:
    return {
        "outcome": "assessed",
        "state": "no_action_needed",
        "summary": claim("Pricing was asked for and sent.", E_PRICING_ASKED),
        "reason": claim("The pricing question was answered.", E_PRICING_SENT),
        "open_items": [],
    }


def insufficient_evidence_reply() -> dict[str, Any]:
    return {"outcome": "insufficient_evidence"}


class FakeProvider:
    """Implements AssessmentProvider. Like a real provider, generate() returns raw
    reply text in script order, or raises the scripted exception. Counts calls and
    keeps the last input.

    A dict in the script is a test convenience only: it is turned into JSON text here,
    so generate() never hands back a parsed object.
    """

    name = "fake"
    model = "fake-model"

    def __init__(self, *replies: str | dict[str, Any] | Exception) -> None:
        self._replies: list[str | Exception] = [
            json.dumps(reply) if isinstance(reply, dict) else reply for reply in replies
        ]
        self.calls = 0
        self.last_input_json: str | None = None

    async def generate(
        self, system_instruction: str, input_json: str, response_schema: dict[str, Any]
    ) -> str:
        self.calls += 1
        self.last_input_json = input_json
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply
