"""Read-only relationship API: list, detail, errors, CORS and startup.

Every test uses its own temporary SQLite file. The developer's customer_pulse.db is
never opened.
"""

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.db import Interaction, create_tables, make_engine
from app.main import create_app
from app.relationships import latest_interaction_summary
from app.seed import seed_database
from app.settings import Settings

FRONTEND_ORIGIN = "http://localhost:3000"
DEVELOPER_DB = Path("customer_pulse.db")


def settings_for(tmp_path: Path) -> Settings:
    # _env_file=None: a developer's backend/.env must not leak into tests.
    return Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'test.db'}")


@pytest.fixture
def seeded_engine(tmp_path: Path) -> Engine:
    engine = make_engine(settings_for(tmp_path).database_url)
    create_tables(engine)
    seed_database(engine)
    return engine


@pytest.fixture
def client(tmp_path: Path, seeded_engine: Engine) -> Iterator[TestClient]:
    with TestClient(create_app(settings_for(tmp_path))) as client:
        yield client


def interaction(id: str, type: str, occurred_at: date) -> Interaction:
    return Interaction(
        id=id,
        customer_id="cust_x",
        contact_id="contact_x",
        type=type,
        occurred_at=occurred_at,
    )


# --- latest-interaction summary (plain function) ---


def test_summary_is_none_without_interactions() -> None:
    assert latest_interaction_summary([]) is None


def test_summary_picks_the_latest_date_not_the_highest_id() -> None:
    summary = latest_interaction_summary(
        [
            interaction("int_9", "call", date(2026, 1, 1)),
            interaction("int_1", "email", date(2026, 3, 1)),
        ]
    )

    assert summary is not None
    assert (summary.date, summary.count, summary.types) == (
        date(2026, 3, 1),
        1,
        ["email"],
    )


def test_summary_counts_every_same_date_interaction_and_lists_distinct_types() -> None:
    summary = latest_interaction_summary(
        [
            interaction("int_3", "note", date(2026, 3, 1)),
            interaction("int_1", "email", date(2026, 3, 1)),
            interaction("int_2", "email", date(2026, 3, 1)),
            interaction("int_0", "meeting", date(2026, 2, 1)),
        ]
    )

    assert summary is not None
    assert summary.count == 3
    assert set(summary.types) == {"email", "note"}


# --- list ---


def test_list_returns_every_seeded_relationship_in_name_order(
    client: TestClient,
) -> None:
    response = client.get("/api/relationships")

    assert response.status_code == 200
    rows = response.json()["relationships"]
    assert len(rows) == 12
    assert {row["id"] for row in rows} == {f"cust_{n:03d}" for n in range(1, 13)}
    names = [row["name"] for row in rows]
    assert names == sorted(names, key=str.casefold)
    for row in rows:
        assert set(row) == {"id", "name", "status", "latest_interaction", "assessment"}
        assert row["status"] in {"prospect", "customer"}
        assert row["assessment"] is None


def test_list_latest_interaction_for_one_and_for_several_on_a_date(
    client: TestClient,
) -> None:
    rows = {
        row["id"]: row
        for row in client.get("/api/relationships").json()["relationships"]
    }

    assert rows["cust_001"]["latest_interaction"] == {
        "date": "2026-08-29",
        "count": 1,
        "types": ["note"],
    }
    # Parkview Dental Studio: two interactions share the latest date. Both types are
    # listed; the test does not say which came first because nothing in the data does.
    parkview = rows["cust_009"]["latest_interaction"]
    assert parkview["date"] == "2026-08-20"
    assert parkview["count"] == 2
    assert set(parkview["types"]) == {"email", "note"}


# --- detail ---


def test_detail_returns_facts_contacts_and_complete_history(client: TestClient) -> None:
    response = client.get("/api/relationships/cust_009")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "id",
        "name",
        "status",
        "created_at",
        "contacts",
        "interactions",
    }
    assert (body["id"], body["name"], body["status"], body["created_at"]) == (
        "cust_009",
        "Parkview Dental Studio",
        "prospect",
        "2026-08-17",
    )
    assert body["contacts"] == [
        {
            "id": "contact_010",
            "name": "Chris Evans",
            "email": "chris@parkviewdental.example",
            "role": "Dentist",
        }
    ]
    history = body["interactions"]
    assert {item["id"] for item in history} == {f"int_{n:03d}" for n in range(36, 41)}
    for item in history:
        assert set(item) == {"id", "type", "occurred_at", "contact_id", "notes"}
        assert item["contact_id"] == "contact_010"
    dates = [item["occurred_at"] for item in history]
    assert dates == sorted(dates, reverse=True)


def test_detail_keeps_every_interaction_that_shares_a_date(client: TestClient) -> None:
    history = client.get("/api/relationships/cust_009").json()["interactions"]

    on_latest_date = [item for item in history if item["occurred_at"] == "2026-08-20"]
    assert {(item["id"], item["type"]) for item in on_latest_date} == {
        ("int_039", "email"),
        ("int_040", "note"),
    }
    assert all(item["notes"] for item in on_latest_date)
    # No field says which of the two happened first, and none is added to say so.
    assert all("sequence" not in item and "position" not in item for item in history)


def test_detail_keeps_the_oldest_interactions(client: TestClient) -> None:
    history = client.get("/api/relationships/cust_010").json()["interactions"]

    assert len(history) == 4
    assert history[-1]["occurred_at"] == min(item["occurred_at"] for item in history)


def test_unknown_relationship_is_404(client: TestClient) -> None:
    response = client.get("/api/relationships/cust_999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Relationship not found"}


# --- CORS ---


def test_configured_frontend_origin_is_allowed(client: TestClient) -> None:
    response = client.get("/api/relationships", headers={"Origin": FRONTEND_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


def test_other_origins_get_no_cors_header(client: TestClient) -> None:
    response = client.get(
        "/api/relationships", headers={"Origin": "http://other.example:3000"}
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_origins_setting_is_comma_separated() -> None:
    settings = Settings(
        _env_file=None, cors_origins="http://localhost:3000, http://127.0.0.1:3000"
    )

    assert settings.cors_origin_list() == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


# --- startup and failures ---


def test_startup_fails_clearly_when_the_database_is_not_seeded(tmp_path: Path) -> None:
    app = create_app(settings_for(tmp_path))

    with pytest.raises(RuntimeError, match="python -m app.seed") as raised:
        with TestClient(app):
            pass

    assert "customers" in str(raised.value)
    assert "interactions" in str(raised.value)


def test_database_failure_is_a_500_not_an_empty_list(
    tmp_path: Path, seeded_engine: Engine
) -> None:
    app = create_app(settings_for(tmp_path))
    with TestClient(app, raise_server_exceptions=False) as client:
        with seeded_engine.begin() as connection:
            connection.execute(text("DROP TABLE interactions"))

        response = client.get("/api/relationships")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal error"}


def test_api_tests_leave_the_developer_database_alone(client: TestClient) -> None:
    before = DEVELOPER_DB.stat().st_mtime_ns if DEVELOPER_DB.exists() else None

    client.get("/api/relationships")
    client.get("/api/relationships/cust_001")

    after = DEVELOPER_DB.stat().st_mtime_ns if DEVELOPER_DB.exists() else None
    assert after == before
