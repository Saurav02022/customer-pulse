"""The assessment route and the provider's place in the app lifecycle.

A fake provider is injected, except where startup and shutdown of the real Gemini
provider are tested; that provider is built but never sends a request.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from assessment_support import (
    EMPTY_NOTES_ID,
    NO_INTERACTIONS_ID,
    RELATIONSHIP_ID,
    FakeProvider,
    action_needed_reply,
    insufficient_evidence_reply,
    no_action_needed_reply,
    store_facts,
    waiting_reply,
)
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.assessment.gemini import GeminiAssessmentProvider
from app.assessment.provider import (
    ProviderEmptyResponse,
    ProviderError,
    ProviderTimeout,
)
from app.db import create_tables, make_engine
from app.main import create_app
from app.settings import Settings

URL = f"/api/relationships/{RELATIONSHIP_ID}/assessment"
SECRET_NOTE = "Private detail from the reply"


def settings_for(tmp_path: Path, **values: Any) -> Settings:
    # _env_file=None: a developer's backend/.env must not leak into tests.
    return Settings(
        _env_file=None, database_url=f"sqlite:///{tmp_path / 'test.db'}", **values
    )


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = make_engine(settings_for(tmp_path).database_url)
    create_tables(engine)
    store_facts(engine)
    return engine


def client_for(tmp_path: Path, provider: FakeProvider) -> TestClient:
    return TestClient(
        create_app(settings_for(tmp_path), provider=provider),
        raise_server_exceptions=False,
    )


@pytest.fixture
def run(tmp_path: Path, engine: Engine) -> Iterator[Any]:
    """Start the app with a fake provider scripted with `replies`."""
    clients: list[TestClient] = []

    def start(*replies: Any) -> tuple[TestClient, FakeProvider]:
        provider = FakeProvider(*replies)
        client = client_for(tmp_path, provider).__enter__()
        clients.append(client)
        return client, provider

    yield start
    for client in clients:
        client.__exit__(None, None, None)


# --- success ---


def test_action_needed_uses_the_public_contract(run) -> None:
    client, _ = run(action_needed_reply())

    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == {
        "status": "assessed",
        "state": "action_needed",
        "summary": {
            "text": "Pricing was asked for and sent.",
            "evidence": ["int_101", "int_103"],
        },
        "reason": {
            "text": "Pricing was sent and no response is recorded.",
            "evidence": ["int_103"],
        },
        "open_items": [
            {
                "text": "Get a reply on the pricing.",
                "evidence": ["int_103"],
                "contact_ids": ["contact_101"],
            }
        ],
        "next_action": {
            "text": "Follow up with Asha on the pricing.",
            "evidence": ["int_103"],
        },
    }


def test_waiting_has_waiting_for_and_a_null_next_action(run) -> None:
    client, _ = run(waiting_reply())

    body = client.get(URL).json()

    assert body["state"] == "waiting"
    assert body["waiting_for"] == {
        "text": "The busy season plan.",
        "evidence": ["int_102"],
    }
    assert body["next_action"] is None


def test_no_action_needed_has_no_next_action_or_waiting_for(run) -> None:
    client, _ = run(no_action_needed_reply())

    body = client.get(URL).json()

    assert body["state"] == "no_action_needed"
    assert body["open_items"] == []
    assert "next_action" not in body
    assert "waiting_for" not in body


def test_second_request_is_served_from_storage(run) -> None:
    client, provider = run(action_needed_reply())

    first = client.get(URL)
    second = client.get(URL)

    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()
    assert provider.calls == 1


def test_insufficient_evidence_is_unavailable_and_stored(run) -> None:
    client, provider = run(insufficient_evidence_reply())

    first = client.get(URL)
    second = client.get(URL)

    expected = {"status": "unavailable", "cause": "insufficient_evidence"}
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() == expected
    assert provider.calls == 1


@pytest.mark.parametrize(
    ("customer_id", "cause"),
    [
        (NO_INTERACTIONS_ID, "no_interactions"),
        (EMPTY_NOTES_ID, "insufficient_evidence"),
    ],
)
def test_code_decided_causes(run, customer_id: str, cause: str) -> None:
    client, provider = run()

    response = client.get(f"/api/relationships/{customer_id}/assessment")

    assert response.status_code == 200
    assert response.json() == {"status": "unavailable", "cause": cause}
    assert provider.calls == 0


def collect_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(collect_keys(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(collect_keys(v) for v in value))
    return set()


@pytest.mark.parametrize(
    "reply", [action_needed_reply(), waiting_reply(), insufficient_evidence_reply()]
)
def test_response_has_no_internal_fields(run, reply: dict[str, Any]) -> None:
    client, _ = run(reply)

    response = client.get(URL)

    internal = {
        "fingerprint",
        "provider",
        "model",
        "prompt_version",
        "result_json",
        "outcome",
        "contacts",
        "created_at",
    }
    assert collect_keys(response.json()) & internal == set()
    assert "e_" not in response.text
    assert "fake" not in response.text


# --- failures ---


@pytest.mark.parametrize(
    ("failure", "status", "cause"),
    [
        (f"not json {SECRET_NOTE}", 502, "invalid_output"),
        ({"outcome": "assessed", "state": "waiting"}, 502, "invalid_output"),
        (ProviderEmptyResponse(f"blocked {SECRET_NOTE}"), 502, "invalid_output"),
        (ProviderTimeout(f"slow {SECRET_NOTE}"), 503, "provider_timeout"),
        (ProviderError(f"HTTP 503 {SECRET_NOTE}"), 503, "provider_error"),
    ],
)
def test_failure_maps_to_its_status_and_cause_and_is_retried(
    run, failure: Any, status: int, cause: str
) -> None:
    client, provider = run(failure, action_needed_reply())

    response = client.get(URL)

    assert response.status_code == status
    body = response.json()
    assert set(body) == {"detail", "cause"}
    assert body["cause"] == cause
    assert SECRET_NOTE not in response.text
    assert "state" not in body
    retried = client.get(URL)
    assert retried.status_code == 200
    assert retried.json()["state"] == "action_needed"
    assert provider.calls == 2


def test_setup_error_is_a_plain_500(run) -> None:
    client, _ = run(RuntimeError("Gemini refused the request (HTTP 401)."))

    response = client.get(URL)

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal error"}


def test_unknown_relationship_is_404(run) -> None:
    client, provider = run()

    response = client.get("/api/relationships/cust_missing/assessment")

    assert response.status_code == 404
    assert response.json() == {"detail": "Relationship not found"}
    assert provider.calls == 0


def test_relationship_list_still_returns_null_assessments(run) -> None:
    # Temporary until the frontend stage changes both sides of the list contract.
    client, _ = run(action_needed_reply())
    assert client.get(URL).status_code == 200

    rows = client.get("/api/relationships").json()["relationships"]

    assert rows
    assert all(row["assessment"] is None for row in rows)


# --- app lifecycle ---


def test_fake_provider_needs_no_key(tmp_path: Path, engine: Engine) -> None:
    settings = settings_for(tmp_path)
    assert settings.gemini_api_key is None

    with TestClient(create_app(settings, provider=FakeProvider())) as client:
        assert client.get("/").status_code == 200


@pytest.mark.parametrize("key", [None, "", "   "])
def test_real_provider_refuses_to_start_without_a_key(
    tmp_path: Path, engine: Engine, key: str | None
) -> None:
    app = create_app(settings_for(tmp_path, gemini_api_key=key))

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        with TestClient(app):
            pass


def test_real_provider_is_created_once_and_closed_on_shutdown(
    tmp_path: Path, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    closed: list[GeminiAssessmentProvider] = []
    original_close = GeminiAssessmentProvider.aclose

    async def recording_close(self: GeminiAssessmentProvider) -> None:
        closed.append(self)
        await original_close(self)

    monkeypatch.setattr(GeminiAssessmentProvider, "aclose", recording_close)
    settings = settings_for(tmp_path, gemini_api_key="dummy-key-not-real")
    app = create_app(settings)

    with TestClient(app) as client:
        provider = app.state.provider
        assert isinstance(provider, GeminiAssessmentProvider)
        client.get("/api/relationships")
        client.get(f"/api/relationships/{NO_INTERACTIONS_ID}/assessment")
        assert app.state.provider is provider
        assert closed == []

    assert closed == [provider]


def test_startup_names_a_missing_assessment_table(
    tmp_path: Path, engine: Engine
) -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE assessments"))
    app = create_app(settings_for(tmp_path), provider=FakeProvider())

    with pytest.raises(RuntimeError, match="assessments.*python -m app.seed"):
        with TestClient(app):
            pass
