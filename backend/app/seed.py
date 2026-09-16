"""Load the tracked seed CSV files into the database.

Run from backend/ with `python -m app.seed`. Every row is validated before anything is
written. Missing rows are inserted in one transaction. A stored row with the same
content is left alone; one with different content aborts the load. So a bad file or a
conflicting row leaves the existing data untouched, and a second run changes nothing.
"""

import csv
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError
from sqlalchemy import Engine, insert, select
from sqlalchemy.orm import Session

from app.db import (
    Contact,
    Customer,
    CustomerStatus,
    Interaction,
    InteractionType,
    create_tables,
    make_engine,
)
from app.settings import Settings

log = logging.getLogger(__name__)

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SeedError(Exception):
    """The seed files are malformed. Nothing was written."""


def _parse_iso_date(value: object) -> date:
    # Only a plain YYYY-MM-DD is accepted; the data has no time of day.
    if not isinstance(value, str) or not _ISO_DATE.match(value):
        raise ValueError("must be a date in YYYY-MM-DD form")
    return date.fromisoformat(value)


IsoDate = Annotated[date, BeforeValidator(_parse_iso_date)]
RequiredText = Annotated[str, Field(min_length=1)]


class _Row(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: RequiredText


class CustomerRow(_Row):
    name: RequiredText
    status: CustomerStatus
    created_at: IsoDate


class ContactRow(_Row):
    customer_id: RequiredText
    name: RequiredText
    email: RequiredText
    role: RequiredText


class InteractionRow(_Row):
    customer_id: RequiredText
    contact_id: RequiredText
    type: InteractionType
    occurred_at: IsoDate
    notes: str


@dataclass(frozen=True)
class SeedData:
    customers: list[CustomerRow]
    contacts: list[ContactRow]
    interactions: list[InteractionRow]


def _read_rows[RowT: _Row](path: Path, row_model: type[RowT]) -> list[RowT]:
    expected_headers = list(row_model.model_fields)
    try:
        with path.open(newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames != expected_headers:
                raise SeedError(
                    f"{path.name}: headers must be exactly {expected_headers}, "
                    f"got {reader.fieldnames}"
                )
            rows = []
            for number, raw in enumerate(reader, start=1):
                if None in raw or None in raw.values():
                    raise SeedError(
                        f"{path.name} row {number}: wrong number of columns"
                    )
                try:
                    rows.append(row_model.model_validate(raw))
                except ValidationError as error:
                    first = error.errors()[0]
                    field = ".".join(str(part) for part in first["loc"]) or "row"
                    raise SeedError(
                        f"{path.name} row {number} (id={raw.get('id')!r}): "
                        f"{field}: {first['msg']}"
                    ) from error
    except OSError as error:
        raise SeedError(f"{path.name}: cannot read file: {error.strerror}") from error
    return rows


def _unique_ids(file_name: str, rows: list[_Row]) -> set[str]:
    seen: set[str] = set()
    for row in rows:
        if row.id in seen:
            raise SeedError(f"{file_name}: duplicate id {row.id!r}")
        seen.add(row.id)
    return seen


def _check_references(data: SeedData) -> None:
    customer_ids = _unique_ids("customers.csv", data.customers)
    contact_ids = _unique_ids("contacts.csv", data.contacts)
    _unique_ids("interactions.csv", data.interactions)

    for contact in data.contacts:
        if contact.customer_id not in customer_ids:
            raise SeedError(
                f"contacts.csv: contact {contact.id!r} references "
                f"unknown customer_id {contact.customer_id!r}"
            )

    customer_of_contact = {contact.id: contact.customer_id for contact in data.contacts}
    for interaction in data.interactions:
        if interaction.customer_id not in customer_ids:
            raise SeedError(
                f"interactions.csv: interaction {interaction.id!r} references "
                f"unknown customer_id {interaction.customer_id!r}"
            )
        if interaction.contact_id not in contact_ids:
            raise SeedError(
                f"interactions.csv: interaction {interaction.id!r} references "
                f"unknown contact_id {interaction.contact_id!r}"
            )
        if customer_of_contact[interaction.contact_id] != interaction.customer_id:
            raise SeedError(
                f"interactions.csv: interaction {interaction.id!r} has customer_id "
                f"{interaction.customer_id!r} but contact {interaction.contact_id!r} "
                f"belongs to customer {customer_of_contact[interaction.contact_id]!r}"
            )


def load_seed(seed_dir: Path = SEED_DIR) -> SeedData:
    """Read and validate all three seed files. Raises SeedError on the first problem."""
    data = SeedData(
        customers=_read_rows(seed_dir / "customers.csv", CustomerRow),
        contacts=_read_rows(seed_dir / "contacts.csv", ContactRow),
        interactions=_read_rows(seed_dir / "interactions.csv", InteractionRow),
    )
    _check_references(data)
    return data


type FactModel = type[Customer] | type[Contact] | type[Interaction]


def _insert_missing(session: Session, model: FactModel, rows: list[_Row]) -> None:
    """Insert rows whose id is new. A stored row with the same id must match exactly."""
    seed_rows = {row.id: row.model_dump() for row in rows}
    existing = session.scalars(select(model).where(model.id.in_(seed_rows))).all()
    for stored in existing:
        seed_row = seed_rows.pop(stored.id)
        differing = sorted(
            field
            for field, value in seed_row.items()
            if getattr(stored, field) != value
        )
        if differing:
            raise SeedError(
                f"{model.__tablename__}: stored row {stored.id!r} differs from the "
                f"seed in {', '.join(differing)}"
            )
    if seed_rows:
        session.execute(insert(model), list(seed_rows.values()))


def seed_database(engine: Engine, seed_dir: Path = SEED_DIR) -> SeedData:
    """Validate the seed files, then add the missing facts in one transaction.

    Facts are never updated or deleted here. A stored row that differs from the seed
    raises SeedError and the whole transaction is rolled back.
    """
    data = load_seed(seed_dir)
    with Session(engine) as session, session.begin():
        _insert_missing(session, Customer, data.customers)
        _insert_missing(session, Contact, data.contacts)
        _insert_missing(session, Interaction, data.interactions)
    return data


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    engine = make_engine(Settings().database_url)
    create_tables(engine)
    data = seed_database(engine)
    log.info(
        "seed data present: %d customers, %d contacts, %d interactions",
        len(data.customers),
        len(data.contacts),
        len(data.interactions),
    )


if __name__ == "__main__":
    main()
