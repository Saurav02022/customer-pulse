"""Read-only relationship routes: list and detail facts.

No AI call is made here. The list adds each relationship's stored assessment outcome,
but only when it matches the current inputs, and never waits for a provider.
"""

from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.assessment.routes import UnavailableOut
from app.assessment.service import (
    AssessmentOutcome,
    Facts,
    Unavailable,
    current_outcomes,
)
from app.db import (
    Contact,
    Customer,
    CustomerStatus,
    Interaction,
    InteractionType,
    get_session,
)

router = APIRouter()


class LatestInteraction(BaseModel):
    date: date
    count: int
    # Distinct types on the latest date, in id order. Id order only keeps the output
    # stable; it says nothing about which interaction happened first on that date.
    types: list[InteractionType]


class ListAssessed(BaseModel):
    """The part of a stored business assessment the list row shows."""

    status: Literal["assessed"] = "assessed"
    state: Literal["action_needed", "waiting", "no_action_needed"]
    reason: str


class RelationshipSummary(BaseModel):
    id: str
    name: str
    status: CustomerStatus
    latest_interaction: LatestInteraction | None
    # None means nothing valid is stored for the current inputs. It is not a business
    # state and not "Assessment unavailable"; the browser asks the assessment route.
    assessment: ListAssessed | UnavailableOut | None


class RelationshipList(BaseModel):
    relationships: list[RelationshipSummary]


class ContactFacts(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    role: str


class InteractionFacts(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: InteractionType
    occurred_at: date
    contact_id: str
    notes: str


class RelationshipDetail(BaseModel):
    id: str
    name: str
    status: CustomerStatus
    created_at: date
    contacts: list[ContactFacts]
    interactions: list[InteractionFacts]


def latest_interaction_summary(
    interactions: Iterable[Interaction],
) -> LatestInteraction | None:
    """Summarise what happened on the latest date, without ordering within that date."""
    interactions = list(interactions)
    if not interactions:
        return None
    latest_date = max(interaction.occurred_at for interaction in interactions)
    on_latest_date = sorted(
        (i for i in interactions if i.occurred_at == latest_date), key=lambda i: i.id
    )
    distinct_types = list(dict.fromkeys(i.type for i in on_latest_date))
    return LatestInteraction(
        date=latest_date, count=len(on_latest_date), types=distinct_types
    )


SessionDep = Annotated[Session, Depends(get_session)]


def _list_assessment(
    outcome: AssessmentOutcome | None,
) -> ListAssessed | UnavailableOut | None:
    if outcome is None:
        return None
    if isinstance(outcome, Unavailable):
        return UnavailableOut(cause=outcome.cause)
    return ListAssessed(state=outcome.state, reason=outcome.reason.text)


@router.get("/api/relationships")
def list_relationships(session: SessionDep, request: Request) -> RelationshipList:
    customers = session.scalars(
        select(Customer).order_by(func.lower(Customer.name), Customer.id)
    ).all()
    # One query each for contacts and interactions instead of one per customer.
    contacts_by_customer: dict[str, list[Contact]] = defaultdict(list)
    for contact in session.scalars(select(Contact)):
        contacts_by_customer[contact.customer_id].append(contact)
    interactions_by_customer: dict[str, list[Interaction]] = defaultdict(list)
    for interaction in session.scalars(select(Interaction)):
        interactions_by_customer[interaction.customer_id].append(interaction)
    # Reads storage only: the provider gives its name and model, and is never called.
    outcomes = current_outcomes(
        session,
        request.app.state.provider,
        {
            customer.id: Facts(
                customer.status,
                contacts_by_customer[customer.id],
                interactions_by_customer[customer.id],
            )
            for customer in customers
        },
    )
    return RelationshipList(
        relationships=[
            RelationshipSummary(
                id=customer.id,
                name=customer.name,
                status=customer.status,
                latest_interaction=latest_interaction_summary(
                    interactions_by_customer[customer.id]
                ),
                assessment=_list_assessment(outcomes[customer.id]),
            )
            for customer in customers
        ]
    )


@router.get("/api/relationships/{customer_id}")
def get_relationship(customer_id: str, session: SessionDep) -> RelationshipDetail:
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Relationship not found")
    contacts = session.scalars(
        select(Contact).where(Contact.customer_id == customer_id).order_by(Contact.id)
    ).all()
    # Newest date first. Within one date, id order is a stable display order only.
    interactions = session.scalars(
        select(Interaction)
        .where(Interaction.customer_id == customer_id)
        .order_by(Interaction.occurred_at.desc(), Interaction.id)
    ).all()
    return RelationshipDetail(
        id=customer.id,
        name=customer.name,
        status=customer.status,
        created_at=customer.created_at,
        contacts=[ContactFacts.model_validate(contact) for contact in contacts],
        interactions=[
            InteractionFacts.model_validate(interaction) for interaction in interactions
        ],
    )
