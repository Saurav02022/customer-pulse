"""Read-only relationship routes: list and detail facts. No AI is involved here."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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


class RelationshipSummary(BaseModel):
    id: str
    name: str
    status: CustomerStatus
    latest_interaction: LatestInteraction | None
    # Filled in by the assessment stage. Null means nothing is stored, which is not
    # "Assessment unavailable".
    assessment: None = None


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


@router.get("/api/relationships")
def list_relationships(session: SessionDep) -> RelationshipList:
    customers = session.scalars(
        select(Customer).order_by(func.lower(Customer.name), Customer.id)
    ).all()
    # One query for every interaction instead of one per customer.
    interactions_by_customer: dict[str, list[Interaction]] = defaultdict(list)
    for interaction in session.scalars(select(Interaction)):
        interactions_by_customer[interaction.customer_id].append(interaction)
    return RelationshipList(
        relationships=[
            RelationshipSummary(
                id=customer.id,
                name=customer.name,
                status=customer.status,
                latest_interaction=latest_interaction_summary(
                    interactions_by_customer[customer.id]
                ),
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
