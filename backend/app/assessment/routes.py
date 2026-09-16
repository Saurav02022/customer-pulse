"""The assessment route: get the stored outcome for one relationship, or generate it.

HTTP only. The lifecycle lives in service.py.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.assessment.contract import (
    ActionNeeded,
    Claim,
    InvalidOutput,
    NoActionNeeded,
    Waiting,
)
from app.assessment.provider import (
    ProviderEmptyResponse,
    ProviderError,
    ProviderTimeout,
)
from app.assessment.service import (
    AssessmentOutcome,
    RelationshipNotFound,
    Unavailable,
    get_or_create_assessment,
)

router = APIRouter()


class ClaimOut(BaseModel):
    text: str
    evidence: list[str]  # real interaction ids


class OpenItemOut(ClaimOut):
    contact_ids: list[str]


class _AssessedOut(BaseModel):
    status: Literal["assessed"] = "assessed"
    summary: ClaimOut
    reason: ClaimOut
    open_items: list[OpenItemOut]


class ActionNeededOut(_AssessedOut):
    state: Literal["action_needed"] = "action_needed"
    next_action: ClaimOut


class WaitingOut(_AssessedOut):
    state: Literal["waiting"] = "waiting"
    waiting_for: ClaimOut
    next_action: ClaimOut | None


class NoActionNeededOut(_AssessedOut):
    # No next_action field at all.
    state: Literal["no_action_needed"] = "no_action_needed"


class UnavailableOut(BaseModel):
    status: Literal["unavailable"] = "unavailable"
    cause: Literal["no_interactions", "insufficient_evidence"]


AssessmentResponse = ActionNeededOut | WaitingOut | NoActionNeededOut | UnavailableOut


class FailureOut(BaseModel):
    detail: str
    cause: Literal["invalid_output", "provider_timeout", "provider_error"]


def _claim(claim: Claim) -> ClaimOut:
    return ClaimOut(text=claim.text, evidence=claim.evidence)


def to_response(outcome: AssessmentOutcome) -> AssessmentResponse:
    if isinstance(outcome, Unavailable):
        return UnavailableOut(cause=outcome.cause)
    common = {
        "summary": _claim(outcome.summary),
        "reason": _claim(outcome.reason),
        "open_items": [
            OpenItemOut(text=i.text, evidence=i.evidence, contact_ids=i.contacts)
            for i in outcome.open_items
        ],
    }
    match outcome:
        case ActionNeeded():
            return ActionNeededOut(**common, next_action=_claim(outcome.next_action))
        case Waiting():
            next_action = outcome.next_action
            return WaitingOut(
                **common,
                waiting_for=_claim(outcome.waiting_for),
                next_action=_claim(next_action) if next_action else None,
            )
        case NoActionNeeded():
            return NoActionNeededOut(**common)


def _failure(status_code: int, cause: str, detail: str) -> JSONResponse:
    body = FailureOut(detail=detail, cause=cause)
    return JSONResponse(status_code=status_code, content=body.model_dump())


@router.get(
    "/api/relationships/{customer_id}/assessment",
    response_model=AssessmentResponse,
    responses={502: {"model": FailureOut}, 503: {"model": FailureOut}},
)
async def get_assessment(
    customer_id: str, request: Request
) -> AssessmentResponse | JSONResponse:
    app_state = request.app.state
    try:
        outcome = await get_or_create_assessment(
            app_state.engine, app_state.provider, customer_id
        )
    except RelationshipNotFound:
        raise HTTPException(status_code=404, detail="Relationship not found") from None
    except (InvalidOutput, ProviderEmptyResponse):
        return _failure(
            502, "invalid_output", "The assessment reply could not be trusted."
        )
    except ProviderTimeout:
        return _failure(
            503, "provider_timeout", "The assessment provider did not reply in time."
        )
    except ProviderError:
        return _failure(
            503, "provider_error", "The assessment provider is temporarily unavailable."
        )
    return to_response(outcome)
