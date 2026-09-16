"""The AI provider boundary.

A provider only sends one request and returns the raw reply text. Parsing, the contract
and grounding stay on our side, so a new provider needs no change to business logic.
"""

from typing import Any, Protocol


class ProviderTimeout(Exception):
    """The call did not finish in time, including its retry."""


class ProviderError(Exception):
    """Rate limit, server error or connection failure, including its retry."""


class ProviderEmptyResponse(Exception):
    """The reply was empty, blocked or truncated. Treated as invalid output."""


class AssessmentProvider(Protocol):
    name: str
    model: str

    async def generate(
        self, system_instruction: str, input_json: str, response_schema: dict[str, Any]
    ) -> str:
        """Return the raw JSON text of the reply.

        Raises ProviderTimeout, ProviderError or ProviderEmptyResponse.
        """
        ...
