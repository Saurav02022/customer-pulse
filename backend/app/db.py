"""SQLite persistence: tables, engine, request sessions and the schema check."""

from collections.abc import Iterator
from datetime import date
from typing import Literal, get_args

from fastapi import Request
from sqlalchemy import (
    CheckConstraint,
    Engine,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    inspect,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

CustomerStatus = Literal["prospect", "customer"]
InteractionType = Literal["email", "call", "meeting", "note"]


def _one_of(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint(
            _one_of("status", get_args(CustomerStatus)), name="ck_customers_status"
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    status: Mapped[str]
    created_at: Mapped[date]


class Contact(Base):
    __tablename__ = "contacts"
    # Lets interactions reference (contact_id, customer_id) as one foreign key.
    __table_args__ = (
        UniqueConstraint("id", "customer_id", name="uq_contacts_id_customer_id"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    name: Mapped[str]
    email: Mapped[str]
    role: Mapped[str]


class Interaction(Base):
    __tablename__ = "interactions"
    __table_args__ = (
        CheckConstraint(
            _one_of("type", get_args(InteractionType)), name="ck_interactions_type"
        ),
        # Rejects an interaction whose contact belongs to another customer.
        ForeignKeyConstraint(
            ["contact_id", "customer_id"],
            ["contacts.id", "contacts.customer_id"],
            name="fk_interactions_contact_customer",
        ),
        Index("ix_interactions_customer_id_occurred_at", "customer_id", "occurred_at"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    contact_id: Mapped[str]
    type: Mapped[str]
    occurred_at: Mapped[date]
    notes: Mapped[str] = mapped_column(Text, server_default="")


def make_engine(database_url: str) -> Engine:
    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _record) -> None:
        # SQLite ignores foreign keys unless every connection turns them on.
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    return engine


def create_tables(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def missing_tables(engine: Engine) -> list[str]:
    """Names of required tables the database does not have, in a stable order."""
    present = set(inspect(engine).get_table_names())
    return sorted(name for name in Base.metadata.tables if name not in present)


def get_session(request: Request) -> Iterator[Session]:
    """One session per request, opened on the app's engine and always closed."""
    with Session(request.app.state.engine) as session:
        yield session
