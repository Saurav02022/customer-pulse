"""AssessmentProvider for Google Gemini, through the official google-genai SDK.

It sends one request and returns the raw reply text. Parsing, the contract and grounding
stay with the caller. SDK exceptions never leave this module: they become the provider
errors, or a setup error for a bad key, model or request.
"""

import asyncio
import logging
import time
from typing import Any

import httpx
from google import genai
from google.genai import errors, types

from app.assessment.provider import (
    ProviderEmptyResponse,
    ProviderError,
    ProviderTimeout,
)
from app.settings import Settings

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30  # per try
TRIES = 2  # one retry, only for a timeout, 429, 5xx or connection error


def _reply_text(response: types.GenerateContentResponse) -> str:
    # A blocked, cut-off or empty reply is not an answer. It never becomes
    # insufficient evidence or a state.
    feedback = response.prompt_feedback
    if feedback is not None and feedback.block_reason is not None:
        raise ProviderEmptyResponse(f"request blocked: {feedback.block_reason}")
    if not response.candidates:
        raise ProviderEmptyResponse("no candidate in the reply")
    finish = response.candidates[0].finish_reason
    if finish != types.FinishReason.STOP:
        raise ProviderEmptyResponse(f"reply not finished: {finish}")
    text = response.text
    if not text or not text.strip():
        raise ProviderEmptyResponse("reply has no text")
    # Raw text on purpose, even if the SDK also parsed it: parse_reply() is the only
    # contract boundary.
    return text


class GeminiAssessmentProvider:
    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        key = settings.gemini_api_key
        if key is None or not key.get_secret_value().strip():
            raise ValueError("GEMINI_API_KEY is not set. Add it to backend/.env.")
        self.model = settings.gemini_model
        # vertexai=False: an environment variable must not move calls to another API.
        # The caller closes the client with `await provider.client.aio.aclose()`.
        self.client = genai.Client(api_key=key.get_secret_value(), vertexai=False)

    async def generate(
        self, system_instruction: str, input_json: str, response_schema: dict[str, Any]
    ) -> str:
        """Return the raw JSON text of the reply.

        Raises ProviderTimeout, ProviderError or ProviderEmptyResponse. A request the
        API refuses as wrong (400, 401, 403, 404) is a setup error and raises
        RuntimeError. Messages hold no key, prompt, input or reply text.
        """
        # No temperature, top_p or top_k: Gemini 3.8 Flash is meant to run with its
        # default sampling.
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_json_schema=response_schema,
        )
        failure: Exception | None = None
        for attempt in range(1, TRIES + 1):
            started = time.monotonic()
            try:
                async with asyncio.timeout(TIMEOUT_SECONDS):
                    response = await self.client.aio.models.generate_content(
                        model=self.model, contents=input_json, config=config
                    )
            except TimeoutError:
                failure = ProviderTimeout(f"no reply within {TIMEOUT_SECONDS} s")
            except errors.APIError as error:
                status = error.code
                if status != 429 and not (status and status >= 500):
                    self._log(attempt, started, f"setup_error http={status}")
                    raise RuntimeError(
                        f"Gemini refused the request (HTTP {status}). "
                        "Check GEMINI_API_KEY and GEMINI_MODEL."
                    ) from None
                failure = ProviderError(f"HTTP {status}")
            except (httpx.TransportError, errors.UnknownApiResponseError) as error:
                # UnknownApiResponseError quotes the response body; only its class
                # name is kept.
                failure = ProviderError(type(error).__name__)
            else:
                try:
                    text = _reply_text(response)
                except ProviderEmptyResponse as empty:
                    self._log(attempt, started, f"ProviderEmptyResponse {empty}")
                    raise
                self._log(attempt, started, "ok")
                return text
            self._log(attempt, started, f"{type(failure).__name__} {failure}")
        assert failure is not None
        raise failure

    def _log(self, attempt: int, started: float, result: str) -> None:
        log.info(
            "gemini call model=%s try=%d/%d duration_ms=%d result=%s",
            self.model,
            attempt,
            TRIES,
            (time.monotonic() - started) * 1000,
            result,
        )
