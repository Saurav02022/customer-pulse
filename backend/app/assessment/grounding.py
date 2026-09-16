"""Grounding checks G1 to G6 on a parsed reply, then handles back to real ids.

Any failure rejects the whole reply: nothing is repaired or partly returned. Code proves
that every claim cites real, non-empty notes of this relationship. Whether a note truly
supports the sentence is judged in the AI evaluation, not here.
"""

import re
from collections.abc import Iterator

from app.assessment.contract import (
    Claim,
    InsufficientEvidence,
    InvalidOutput,
    ModelResult,
    OpenItem,
)
from app.assessment.model_input import EvidenceMap

REASON_MAX_LENGTH = 200
CLAIM_MAX_LENGTH = 300

# Real ids are matched by their current seed form (cust_001, int_039).
# Widen this if ids ever change shape.
_ID_OR_HANDLE = re.compile(
    r"\b(?:[ec]_[0-9a-f]{10}|(?:cust|contact|int)_\d+)\b", re.IGNORECASE
)


def _claims(result: ModelResult) -> Iterator[tuple[str, Claim, int]]:
    yield "summary", result.summary, CLAIM_MAX_LENGTH
    yield "reason", result.reason, REASON_MAX_LENGTH
    for number, item in enumerate(result.open_items):
        yield f"open_items[{number}]", item, CLAIM_MAX_LENGTH
    # waiting_for exists only on Waiting; next_action is absent on No action needed.
    for field in ("waiting_for", "next_action"):
        claim = getattr(result, field, None)
        if claim is not None:
            yield field, claim, CLAIM_MAX_LENGTH


def _check(path: str, claim: Claim, max_length: int, evidence: EvidenceMap) -> None:
    for number, cited in enumerate(claim.evidence):
        record = evidence.interactions.get(cited)
        if record is None:
            raise InvalidOutput("G1", f"{path}.evidence[{number}]")
        if not record.has_notes:
            raise InvalidOutput("G2", f"{path}.evidence[{number}]")
    # The contract already requires one handle; this keeps G3 true on its own.
    if not claim.evidence:
        raise InvalidOutput("G3", f"{path}.evidence")
    if isinstance(claim, OpenItem):
        cited_contacts = {
            evidence.interactions[h].contact_handle for h in claim.evidence
        }
        for number, contact in enumerate(claim.contacts):
            if contact not in evidence.contacts or contact not in cited_contacts:
                raise InvalidOutput("G4", f"{path}.contacts[{number}]")
    if _ID_OR_HANDLE.search(claim.text):
        raise InvalidOutput("G5", f"{path}.text")
    if len(claim.text) > max_length:
        raise InvalidOutput("G6", f"{path}.text")


def _resolve(claim: Claim, evidence: EvidenceMap) -> Claim:
    # dict.fromkeys removes duplicates and keeps the model's order.
    update = {
        "evidence": list(
            dict.fromkeys(evidence.interactions[h].id for h in claim.evidence)
        )
    }
    if isinstance(claim, OpenItem):
        update["contacts"] = list(
            dict.fromkeys(evidence.contacts[h] for h in claim.contacts)
        )
    return claim.model_copy(update=update)


def check_grounding(result: ModelResult, evidence: EvidenceMap) -> ModelResult:
    """Run G1 to G6 on every claim, then return the result with real ids.

    Raises InvalidOutput on the first failure. An insufficient-evidence answer has no
    claims and is returned unchanged.
    """
    if isinstance(result, InsufficientEvidence):
        return result
    for path, claim, max_length in _claims(result):
        _check(path, claim, max_length, evidence)
    # Only reached when every claim passed, so no partly trusted result exists.
    update = {
        "summary": _resolve(result.summary, evidence),
        "reason": _resolve(result.reason, evidence),
        "open_items": [_resolve(item, evidence) for item in result.open_items],
    }
    for field in ("waiting_for", "next_action"):
        claim = getattr(result, field, None)
        if claim is not None:
            update[field] = _resolve(claim, evidence)
    return result.model_copy(update=update)
