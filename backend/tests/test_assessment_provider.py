"""The provider boundary, driven through a fake provider. No network, no real model."""

import json

import pytest
from assessment_support import (
    E_FOREIGN,
    FakeProvider,
    action_needed_reply,
    insufficient_evidence_reply,
    sample_input,
)

from app.assessment.contract import (
    ActionNeeded,
    InsufficientEvidence,
    InvalidOutput,
    ModelResult,
    parse_reply,
)
from app.assessment.grounding import check_grounding
from app.assessment.provider import (
    AssessmentProvider,
    ProviderEmptyResponse,
    ProviderError,
    ProviderTimeout,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def assess(provider: AssessmentProvider) -> ModelResult:
    # The same steps the lifecycle will take with a real provider.
    data, evidence = sample_input()
    raw = await provider.generate("system instruction", json.dumps(data), {})
    return check_grounding(parse_reply(raw), evidence)


async def generate(provider: FakeProvider) -> object:
    return await provider.generate("system instruction", "{}", {})


async def test_fake_returns_scripted_raw_text_unchanged() -> None:
    raw = '{"outcome": "insufficient_evidence"}  '
    reply = await generate(FakeProvider(raw))
    assert type(reply) is str
    assert reply == raw
    assert isinstance(parse_reply(reply), InsufficientEvidence)


async def test_fake_turns_a_scripted_dict_into_json_text() -> None:
    scripted = action_needed_reply()
    reply = await generate(FakeProvider(scripted))
    # Raw text, never the dict or a parsed model: parsing is the caller's job.
    assert type(reply) is str
    assert json.loads(reply) == scripted
    assert isinstance(parse_reply(reply), ActionNeeded)


async def test_success_returns_a_trusted_result_with_real_ids() -> None:
    provider = FakeProvider(action_needed_reply())
    result = await assess(provider)
    assert isinstance(result, ActionNeeded)
    assert result.next_action.evidence == ["int_103"]
    assert provider.calls == 1


async def test_provider_gets_handles_never_real_ids() -> None:
    provider = FakeProvider(action_needed_reply())
    await assess(provider)
    assert provider.last_input_json is not None
    assert "int_" not in provider.last_input_json
    assert "contact_" not in provider.last_input_json


async def test_insufficient_evidence_is_a_valid_non_business_outcome() -> None:
    result = await assess(FakeProvider(insufficient_evidence_reply()))
    assert isinstance(result, InsufficientEvidence)
    assert not hasattr(result, "state")


@pytest.mark.parametrize(
    "failure",
    [ProviderTimeout(), ProviderError(), ProviderEmptyResponse()],
    ids=["timeout", "error", "empty"],
)
async def test_provider_failure_propagates_as_its_own_type(failure: Exception) -> None:
    provider = FakeProvider(failure)
    with pytest.raises(type(failure)):
        await assess(provider)
    assert provider.calls == 1


async def test_malformed_reply_is_invalid_output() -> None:
    with pytest.raises(InvalidOutput) as error:
        await assess(FakeProvider('{"outcome": "assessed", "state": '))
    assert error.value.check == "json"


async def test_ungrounded_reply_is_invalid_output() -> None:
    reply = action_needed_reply()
    reply["next_action"]["evidence"] = [E_FOREIGN]
    with pytest.raises(InvalidOutput) as error:
        await assess(FakeProvider(reply))
    assert error.value.check == "G1"


async def test_scripted_replies_are_used_in_order() -> None:
    provider = FakeProvider(ProviderTimeout(), insufficient_evidence_reply())
    with pytest.raises(ProviderTimeout):
        await assess(provider)
    assert isinstance(await assess(provider), InsufficientEvidence)
    assert provider.calls == 2
