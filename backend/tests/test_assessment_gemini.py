"""The Gemini provider. The real SDK client is built, but its one network method is
replaced by a fake, so no request leaves the machine and no real key is needed."""

import asyncio
import json
import logging
from typing import Any

import httpx
import pytest
from assessment_support import action_needed_reply, sample_input
from google.genai import errors, types

from app.assessment import gemini
from app.assessment.contract import RESPONSE_SCHEMA, ActionNeeded, parse_reply
from app.assessment.gemini import GeminiAssessmentProvider
from app.assessment.grounding import check_grounding
from app.assessment.model_input import canonical_json
from app.assessment.prompt import SYSTEM_INSTRUCTION
from app.assessment.provider import (
    AssessmentProvider,
    ProviderEmptyResponse,
    ProviderError,
    ProviderTimeout,
)
from app.settings import Settings

pytestmark = pytest.mark.anyio

TEST_KEY = "test-key-not-real-7c1f"
MODEL = "gemini-test-model"
NOTE = "Private note about pricing."
REPLY_JSON = '{"outcome": "insufficient_evidence"}'
HANG = object()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def reply(
    text: str | None = REPLY_JSON,
    finish: types.FinishReason | None = types.FinishReason.STOP,
) -> types.GenerateContentResponse:
    parts = None if text is None else [types.Part(text=text)]
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(role="model", parts=parts),
                finish_reason=finish,
            )
        ]
    )


def api_error(cls: type[errors.APIError], code: int) -> errors.APIError:
    # The SDK puts the response body in the message; it must never get further.
    body = {"error": {"code": code, "message": f"{TEST_KEY} {NOTE}", "status": "X"}}
    return cls(code, body)


class FakeModels:
    """Stands in for client.aio.models. Plays scripted outcomes in order."""

    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    async def generate_content(self, **kwargs: Any) -> types.GenerateContentResponse:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if outcome is HANG:
            await asyncio.sleep(5)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def make_provider(
    monkeypatch: pytest.MonkeyPatch, *outcomes: Any
) -> tuple[GeminiAssessmentProvider, FakeModels]:
    settings = Settings(_env_file=None, gemini_api_key=TEST_KEY, gemini_model=MODEL)
    provider = GeminiAssessmentProvider(settings)
    fake = FakeModels(*outcomes)
    monkeypatch.setattr(
        provider.client.aio.models, "generate_content", fake.generate_content
    )
    return provider, fake


async def generate(provider: AssessmentProvider) -> str:
    input_json = canonical_json({"notes": NOTE})
    return await provider.generate(SYSTEM_INSTRUCTION, input_json, RESPONSE_SCHEMA)


def assert_safe(error: BaseException) -> None:
    for secret in (TEST_KEY, NOTE, SYSTEM_INSTRUCTION[:40], REPLY_JSON):
        assert secret not in str(error)
    # No SDK exception, which quotes the response body, is chained on.
    assert error.__cause__ is None
    assert error.__context__ is None or error.__suppress_context__


# --- setup ---


@pytest.mark.parametrize("key", [None, "", "   "])
def test_missing_key_is_refused(key: str | None) -> None:
    settings = Settings(_env_file=None, gemini_api_key=key)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiAssessmentProvider(settings)


def test_name_and_model_come_from_settings() -> None:
    settings = Settings(_env_file=None, gemini_api_key=TEST_KEY, gemini_model=MODEL)
    provider = GeminiAssessmentProvider(settings)
    assert (provider.name, provider.model) == ("gemini", MODEL)
    assert TEST_KEY not in repr(settings)


def test_default_model_is_the_approved_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert Settings(_env_file=None).gemini_model == "gemini-3.8-flash"


# --- success ---


async def test_sends_one_structured_request_and_returns_raw_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = '{"outcome":"insufficient_evidence","state":null}  '
    provider, fake = make_provider(monkeypatch, reply(raw))
    assert await generate(provider) == raw

    [call] = fake.calls
    assert call["model"] == MODEL
    assert set(call) == {"model", "contents", "config"}
    # The input goes as the message content, apart from the instruction.
    assert call["contents"] == canonical_json({"notes": NOTE})
    config = call["config"]
    assert isinstance(config, types.GenerateContentConfig)
    assert config.system_instruction == SYSTEM_INSTRUCTION
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == RESPONSE_SCHEMA
    assert config.response_schema is None
    # The model's default sampling is used.
    assert (config.temperature, config.top_p, config.top_k) == (None, None, None)


async def test_log_has_no_key_prompt_input_or_reply(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    provider, _ = make_provider(
        monkeypatch, api_error(errors.ServerError, 503), reply()
    )
    with caplog.at_level(logging.DEBUG, logger="app.assessment.gemini"):
        await generate(provider)
    logged = caplog.text
    assert "try=1/2" in logged and "try=2/2" in logged and MODEL in logged
    for secret in (TEST_KEY, NOTE, SYSTEM_INSTRUCTION[:40], REPLY_JSON):
        assert secret not in logged


# --- retry once, only for temporary failures ---


TEMPORARY = {
    "rate limit": api_error(errors.ClientError, 429),
    "server error": api_error(errors.ServerError, 503),
    "connection": httpx.ConnectError("connection refused"),
    "read error": httpx.ReadError("connection reset"),
    "unreadable body": errors.UnknownApiResponseError(f"Raw response: {NOTE}"),
}


@pytest.mark.parametrize("failure", TEMPORARY.values(), ids=TEMPORARY.keys())
async def test_one_temporary_failure_is_retried(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    provider, fake = make_provider(monkeypatch, failure, reply())
    assert await generate(provider) == REPLY_JSON
    assert len(fake.calls) == 2


@pytest.mark.parametrize("failure", TEMPORARY.values(), ids=TEMPORARY.keys())
async def test_two_temporary_failures_are_a_provider_error(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    provider, fake = make_provider(monkeypatch, failure, failure)
    with pytest.raises(ProviderError) as error:
        await generate(provider)
    assert len(fake.calls) == 2
    assert_safe(error.value)


async def test_two_timeouts_are_a_provider_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gemini, "TIMEOUT_SECONDS", 0.01)
    provider, fake = make_provider(monkeypatch, HANG, HANG)
    with pytest.raises(ProviderTimeout) as error:
        await generate(provider)
    assert len(fake.calls) == 2
    assert_safe(error.value)


async def test_a_timeout_then_a_reply_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini, "TIMEOUT_SECONDS", 0.01)
    provider, fake = make_provider(monkeypatch, HANG, reply())
    assert await generate(provider) == REPLY_JSON
    assert len(fake.calls) == 2


async def test_timeout_then_server_error_reports_the_last_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gemini, "TIMEOUT_SECONDS", 0.01)
    provider, _ = make_provider(monkeypatch, HANG, api_error(errors.ServerError, 500))
    with pytest.raises(ProviderError):
        await generate(provider)


# --- setup errors: not retried, not a temporary failure ---


@pytest.mark.parametrize("code", [400, 401, 403, 404])
async def test_refused_request_is_a_setup_error(
    monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    provider, fake = make_provider(monkeypatch, api_error(errors.ClientError, code))
    with pytest.raises(RuntimeError, match=f"HTTP {code}") as error:
        await generate(provider)
    assert not isinstance(error.value, ProviderError)
    assert len(fake.calls) == 1
    assert_safe(error.value)


# --- empty, blocked or cut-off replies ---


EMPTY = {
    "no text part": reply(text=None),
    "blank text": reply(text="  \n"),
    "cut off": reply(text='{"outcome": "ass', finish=types.FinishReason.MAX_TOKENS),
    "safety stop": reply(text=REPLY_JSON, finish=types.FinishReason.SAFETY),
    "no finish reason": reply(finish=None),
    "no candidates": types.GenerateContentResponse(candidates=[]),
    "blocked request": types.GenerateContentResponse(
        prompt_feedback=types.GenerateContentResponsePromptFeedback(
            block_reason=types.BlockedReason.SAFETY
        )
    ),
    "thought only": types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model", parts=[types.Part(text="thinking", thought=True)]
                ),
                finish_reason=types.FinishReason.STOP,
            )
        ]
    ),
}


@pytest.mark.parametrize("response", EMPTY.values(), ids=EMPTY.keys())
async def test_unusable_reply_is_an_empty_response(
    monkeypatch: pytest.MonkeyPatch, response: types.GenerateContentResponse
) -> None:
    provider, fake = make_provider(monkeypatch, response)
    with pytest.raises(ProviderEmptyResponse) as error:
        await generate(provider)
    # Never retried, and never turned into a decline or a state.
    assert len(fake.calls) == 1
    assert_safe(error.value)


async def test_other_errors_are_not_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    # A bug is not a provider failure: it must not turn into "try again".
    provider, fake = make_provider(monkeypatch, KeyError("bug"))
    with pytest.raises(KeyError):
        await generate(provider)
    assert len(fake.calls) == 1


# --- the provider inside the real validation pipeline, no network ---


async def test_gemini_reply_goes_through_contract_and_grounding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data, evidence = sample_input()
    model_reply = {name: None for name in RESPONSE_SCHEMA["properties"]}
    model_reply |= action_needed_reply()
    provider, fake = make_provider(monkeypatch, reply(json.dumps(model_reply)))

    raw = await provider.generate(
        SYSTEM_INSTRUCTION, canonical_json(data), RESPONSE_SCHEMA
    )
    result = check_grounding(parse_reply(raw), evidence)

    assert isinstance(result, ActionNeeded)
    assert result.summary.evidence == ["int_101", "int_103"]
    assert result.open_items[0].contacts == ["contact_101"]
    assert result.next_action.evidence == ["int_103"]
    sent = fake.calls[0]["contents"]
    assert json.loads(sent) == data
    assert "int_" not in sent and "contact_" not in sent
