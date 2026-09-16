"""The model input for one relationship, and its opaque evidence handles.

The model never sees real ids, because their numbers suggest an order. Each interaction
and contact gets a handle instead, and the backend keeps the map back to the real ids.
Order comes only from `date` values: interactions sharing a date form an unordered
group, listed by handle. Note text is passed as data only.
"""

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from operator import itemgetter
from typing import Any

from app.assessment.contract import RESPONSE_SCHEMA
from app.assessment.prompt import PROMPT_VERSION, SYSTEM_INSTRUCTION
from app.db import Contact, CustomerStatus, Interaction


def handle(prefix: str, real_id: str) -> str:
    # Stable for the same id, but a hash keeps no order: sorting handles says nothing
    # about id order or dates.
    return prefix + hashlib.sha256(real_id.encode()).hexdigest()[:10]


@dataclass(frozen=True)
class InteractionEvidence:
    id: str
    contact_handle: str
    has_notes: bool


@dataclass(frozen=True)
class EvidenceMap:
    """Handle to real record, for one request. Holds only this relationship's records,
    so a handle from another relationship cannot resolve."""

    interactions: dict[str, InteractionEvidence]
    contacts: dict[str, str]  # contact handle to contact id


def _handles(prefix: str, ids: Iterable[str]) -> dict[str, str]:
    """Real id to handle. A repeated handle is a bug (duplicate id or hash clash)."""
    by_handle: dict[str, str] = {}
    for real_id in ids:
        new = handle(prefix, real_id)
        if new in by_handle:
            raise ValueError(f"handle {new} is not unique in this relationship")
        by_handle[new] = real_id
    return {real_id: new for new, real_id in by_handle.items()}


def build_model_input(
    status: CustomerStatus,
    contacts: Iterable[Contact],
    interactions: Iterable[Interaction],
) -> tuple[dict[str, Any], EvidenceMap]:
    """Build the JSON document sent to the model, and the map to read its reply.

    Only the fields the model needs are sent: no customer name, no emails, no real ids,
    no current date. Empty notes are sent as null so they cannot be cited.
    """
    contacts = list(contacts)
    interactions = list(interactions)
    contact_handles = _handles("c_", (contact.id for contact in contacts))
    interaction_handles = _handles("e_", (i.id for i in interactions))

    evidence: dict[str, InteractionEvidence] = {}
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for interaction in interactions:
        own_handle = interaction_handles[interaction.id]
        contact_handle = contact_handles[interaction.contact_id]
        notes = interaction.notes if interaction.notes.strip() else None
        evidence[own_handle] = InteractionEvidence(
            id=interaction.id,
            contact_handle=contact_handle,
            has_notes=notes is not None,
        )
        by_date[interaction.occurred_at.isoformat()].append(
            {
                "handle": own_handle,
                "type": interaction.type,
                "contact": contact_handle,
                "notes": notes,
            }
        )

    by_handle = itemgetter("handle")
    model_input = {
        "relationship_status": status,
        "contacts": sorted(
            (
                {"handle": contact_handles[c.id], "name": c.name, "role": c.role}
                for c in contacts
            ),
            key=by_handle,
        ),
        "interaction_dates": [
            {
                "date": day,
                "same_date_group": "unordered",
                # Sorted by handle only so the input is the same on every run.
                "interactions": sorted(by_date[day], key=by_handle),
            }
            for day in sorted(by_date)  # ISO dates, oldest first
        ],
    }
    return model_input, EvidenceMap(
        interactions=evidence,
        contacts={new: real_id for real_id, new in contact_handles.items()},
    )


def canonical_json(value: Any) -> str:
    """The same text for the same data on every run: sorted keys, fixed separators.

    Used for the input sent to the model and for the fingerprint, so a stored result
    can be matched to exactly what the model saw.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def fingerprint(model_input: dict[str, Any], provider: str, model: str) -> str:
    """Identity of one assessment's inputs. It changes only when the model input, the
    prompt, the response schema, the provider or the model changes; never with time.

    Keys and other settings are not inputs, so they can never change it.
    """
    # prompt_sha catches a prompt or schema edit made without a version bump.
    prompt_sha = _sha256(SYSTEM_INSTRUCTION + canonical_json(RESPONSE_SCHEMA))
    return _sha256(
        canonical_json(
            {
                "prompt_version": PROMPT_VERSION,
                "prompt_sha": prompt_sha,
                "provider": provider,
                "model": model,
                "input": model_input,
            }
        )
    )
