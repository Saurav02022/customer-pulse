import csv
import shutil
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Contact, Customer, Interaction, create_tables, make_engine
from app.seed import SEED_DIR, SeedError, seed_database

EXPECTED_COUNTS = {Customer: 12, Contact: 15, Interaction: 56}


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    create_tables(engine)
    return engine


def count_rows(engine: Engine) -> dict[type, int]:
    with Session(engine) as session:
        return {
            model: session.scalar(select(func.count()).select_from(model))
            for model in EXPECTED_COUNTS
        }


def copy_seed_with_change(tmp_path: Path, file_name: str, edit) -> Path:
    """Copy the real seed files to tmp_path, then let `edit` change one file's rows."""
    seed_dir = tmp_path / "seed"
    shutil.copytree(SEED_DIR, seed_dir)
    path = seed_dir / file_name
    with path.open(newline="") as file:
        rows = list(csv.reader(file))
    edit(rows)
    with path.open("w", newline="") as file:
        csv.writer(file).writerows(rows)
    return seed_dir


def test_seed_loads_the_supplied_dataset(engine: Engine) -> None:
    data = seed_database(engine)

    assert count_rows(engine) == EXPECTED_COUNTS
    assert (len(data.customers), len(data.contacts), len(data.interactions)) == (
        12,
        15,
        56,
    )
    with Session(engine) as session:
        first = session.get(Interaction, "int_001")
    assert first is not None
    assert first.occurred_at == date(2026, 8, 18)
    assert first.notes.startswith("Sarah asked for pricing")


def test_seeding_twice_does_not_duplicate_rows(engine: Engine) -> None:
    seed_database(engine)

    # data_version moves only when another connection commits a change to the file,
    # so an unchanged value proves the second run wrote nothing at all.
    with engine.connect() as watcher:
        version_before = watcher.scalar(text("PRAGMA data_version"))
        seed_database(engine)
        version_after = watcher.scalar(text("PRAGMA data_version"))

    assert version_after == version_before
    assert count_rows(engine) == EXPECTED_COUNTS


def test_seeding_keeps_rows_the_seed_does_not_know(engine: Engine) -> None:
    seed_database(engine)
    extra = {
        "id": "cust_extra",
        "name": "Not in the seed",
        "status": "customer",
        "created_at": date(2026, 1, 1),
    }
    with Session(engine) as session, session.begin():
        session.execute(insert(Customer).values(extra))

    seed_database(engine)

    with Session(engine) as session:
        assert session.get(Customer, "cust_extra") is not None
    assert count_rows(engine) == {**EXPECTED_COUNTS, Customer: 13}


def test_stored_row_with_different_content_aborts_the_whole_seed(
    engine: Engine,
) -> None:
    # cust_009 and contact_010 match the seed; int_040 shares its id, not its content.
    # Customers and contacts are inserted before interactions, so a rollback is the
    # only way the counts can stay at one row each.
    with Session(engine) as session, session.begin():
        session.execute(
            insert(Customer).values(
                id="cust_009",
                name="Parkview Dental Studio",
                status="prospect",
                created_at=date(2026, 8, 17),
            )
        )
        session.execute(
            insert(Contact).values(
                id="contact_010",
                customer_id="cust_009",
                name="Chris Evans",
                email="chris@parkviewdental.example",
                role="Dentist",
            )
        )
        session.execute(
            insert(Interaction).values(
                id="int_040",
                customer_id="cust_009",
                contact_id="contact_010",
                type="email",
                occurred_at=date(2026, 8, 20),
                notes="Edited by hand.",
            )
        )

    with pytest.raises(SeedError) as raised:
        seed_database(engine)

    message = str(raised.value)
    assert "interactions" in message
    assert "int_040" in message
    assert "notes, type" in message
    assert "onboarding" not in message  # the seed's note text is not dumped
    assert count_rows(engine) == {Customer: 1, Contact: 1, Interaction: 1}
    with Session(engine) as session:
        stored = session.get(Interaction, "int_040")
    assert stored is not None
    assert (stored.type, stored.notes) == ("email", "Edited by hand.")


def test_seeded_references_are_consistent(engine: Engine) -> None:
    seed_database(engine)

    with Session(engine) as session:
        contacts_without_customer = session.scalar(
            select(func.count())
            .select_from(Contact)
            .outerjoin(Customer, Customer.id == Contact.customer_id)
            .where(Customer.id.is_(None))
        )
        interactions_without_owner = session.scalar(
            select(func.count())
            .select_from(Interaction)
            .outerjoin(Customer, Customer.id == Interaction.customer_id)
            .outerjoin(Contact, Contact.id == Interaction.contact_id)
            .where((Customer.id.is_(None)) | (Contact.id.is_(None)))
        )
        interactions_with_foreign_contact = session.scalar(
            select(func.count())
            .select_from(Interaction)
            .join(Contact, Contact.id == Interaction.contact_id)
            .where(Contact.customer_id != Interaction.customer_id)
        )

    assert contacts_without_customer == 0
    assert interactions_without_owner == 0
    assert interactions_with_foreign_contact == 0


def set_cell(row_id: str, column: int, value: str):
    def edit(rows: list[list[str]]) -> None:
        row = next(row for row in rows if row[0] == row_id)
        row[column] = value

    return edit


def duplicate_row(row_id: str):
    def edit(rows: list[list[str]]) -> None:
        rows.append(next(row for row in rows if row[0] == row_id))

    return edit


def rename_header(column: int, name: str):
    def edit(rows: list[list[str]]) -> None:
        rows[0][column] = name

    return edit


MALFORMED_CASES = [
    pytest.param(
        "interactions.csv",
        set_cell("int_045", 2, "contact_001"),
        "int_045",
        "belongs to customer 'cust_001'",
        id="contact_of_another_customer",
    ),
    pytest.param(
        "customers.csv",
        set_cell("cust_003", 2, "lead"),
        "cust_003",
        "status",
        id="bad_status",
    ),
    pytest.param(
        "interactions.csv",
        set_cell("int_007", 3, "sms"),
        "int_007",
        "type",
        id="bad_type",
    ),
    pytest.param(
        "interactions.csv",
        set_cell("int_010", 4, "2026-07-18T09:00:00"),
        "int_010",
        "YYYY-MM-DD",
        id="date_with_time",
    ),
    pytest.param(
        "contacts.csv",
        duplicate_row("contact_004"),
        "contact_004",
        "duplicate id",
        id="dup_id",
    ),
    pytest.param(
        "interactions.csv",
        set_cell("int_020", 1, "cust_999"),
        "int_020",
        "unknown customer_id",
        id="unknown_customer",
    ),
    pytest.param(
        "customers.csv",
        rename_header(3, "created"),
        "customers.csv",
        "headers",
        id="bad_header",
    ),
]


@pytest.mark.parametrize(("file_name", "edit", "mentions", "reason"), MALFORMED_CASES)
def test_malformed_seed_is_rejected_and_old_data_kept(
    engine: Engine, tmp_path: Path, file_name: str, edit, mentions: str, reason: str
) -> None:
    seed_database(engine)
    bad_seed_dir = copy_seed_with_change(tmp_path, file_name, edit)

    with pytest.raises(SeedError) as raised:
        seed_database(engine, bad_seed_dir)

    assert file_name in str(raised.value)
    assert mentions in str(raised.value)
    assert reason in str(raised.value)
    assert count_rows(engine) == EXPECTED_COUNTS


def test_malformed_seed_leaves_an_empty_database_empty(
    engine: Engine, tmp_path: Path
) -> None:
    bad_seed_dir = copy_seed_with_change(
        tmp_path, "contacts.csv", set_cell("contact_001", 1, "cust_999")
    )

    with pytest.raises(SeedError, match="unknown customer_id"):
        seed_database(engine, bad_seed_dir)

    assert count_rows(engine) == {Customer: 0, Contact: 0, Interaction: 0}


def test_database_rejects_interaction_whose_contact_belongs_to_another_customer(
    engine: Engine,
) -> None:
    seed_database(engine)

    foreign_contact = {
        "id": "int_x",
        "customer_id": "cust_002",
        "contact_id": "contact_001",
        "type": "note",
        "occurred_at": date(2026, 8, 1),
        "notes": "",
    }

    with Session(engine) as session, pytest.raises(IntegrityError):
        session.execute(insert(Interaction).values(foreign_contact))
        session.commit()
