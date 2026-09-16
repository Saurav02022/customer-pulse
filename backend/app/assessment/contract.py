"""The AI assessment contract: the reply shapes a model may return, and parsing.

The state rules live in the types. Assessment unavailable is not in the union; it is the
API's answer when no valid assessment exists.
"""

import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


class InvalidOutput(Exception):
    """The reply cannot be trusted and must not be stored or shown.

    `check` is "json", "contract" or a grounding check id ("G1" to "G6"). `path` names
    the field. Neither ever holds reply text or note text, so both are safe to log.
    """

    def __init__(self, check: str, path: str = "") -> None:
        super().__init__(f"{check} {path}".strip())
        self.check = check
        self.path = path


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# At least one non-space character. Length limits are grounding check G6.
Text = Annotated[str, Field(pattern=r"\S")]


class Claim(_Strict):
    text: Text
    evidence: list[str] = Field(min_length=1)  # opaque evidence handles


class OpenItem(Claim):
    contacts: list[str] = Field(min_length=1)  # opaque contact handles


class InsufficientEvidence(_Strict):
    """The model declined. A valid outcome, not a business state."""

    outcome: Literal["insufficient_evidence"]


class _Assessed(_Strict):
    outcome: Literal["assessed"]
    summary: Claim
    reason: Claim


class ActionNeeded(_Assessed):
    state: Literal["action_needed"]
    open_items: list[OpenItem]
    next_action: Claim


class Waiting(_Assessed):
    state: Literal["waiting"]
    open_items: list[OpenItem]
    waiting_for: Claim
    # Must apply only after the awaited event. Code cannot check that; the AI
    # evaluation does.
    next_action: Claim | None = None


class NoActionNeeded(_Assessed):
    state: Literal["no_action_needed"]
    # There is no next_action field, so extra="forbid" rejects one.
    open_items: list[OpenItem] = Field(max_length=0)


BusinessAssessment = Annotated[
    ActionNeeded | Waiting | NoActionNeeded, Field(discriminator="state")
]
ModelResult = Annotated[
    InsufficientEvidence | BusinessAssessment, Field(discriminator="outcome")
]

_model_result: TypeAdapter[ModelResult] = TypeAdapter(ModelResult)

# --- The schema sent to the model ---
#
# Providers accept only part of JSON Schema (Gemini has no "const" or "pattern"), so the
# model gets one flat object built from the union members: `outcome` and `state` become
# enums, and every field except `outcome` may be null. It describes structure only.
# parse_reply() still enforces the union and every state rule.

_OUTCOMES = (InsufficientEvidence, ActionNeeded, Waiting, NoActionNeeded)
_NOT_SENT = {"title", "description", "default", "pattern"}
_NULL = {"type": "null"}


def _inline(node: Any, defs: dict[str, Any]) -> Any:
    """Resolve $ref and drop keywords the model does not need or cannot use."""
    if isinstance(node, list):
        return [_inline(item, defs) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return _inline(defs[node["$ref"].removeprefix("#/$defs/")], defs)
    return {
        key: (
            {name: _inline(field, defs) for name, field in value.items()}
            if key == "properties"
            else _inline(value, defs)
        )
        for key, value in node.items()
        if key not in _NOT_SENT
    }


def _flat_response_schema() -> dict[str, Any]:
    enums: dict[str, list[str]] = {}
    fields: dict[str, Any] = {}
    for model in _OUTCOMES:
        schema = model.model_json_schema()
        for name, field in schema["properties"].items():
            field = _inline(field, schema.get("$defs", {}))
            if "const" in field:
                values = enums.setdefault(name, [])
                if field["const"] not in values:
                    values.append(field["const"])
                continue
            # Every field becomes nullable below, and parse_reply() enforces the
            # empty open_items of No action needed.
            field = next(s for s in field.get("anyOf", [field]) if s != _NULL)
            field.pop("maxItems", None)
            if fields.setdefault(name, field) != field:
                raise ValueError(f"field {name} has different shapes across outcomes")

    properties = {"outcome": {"type": "string", "enum": enums.pop("outcome")}}
    for name, values in enums.items():
        properties[name] = {"anyOf": [{"type": "string", "enum": values}, _NULL]}
    for name, field in fields.items():
        properties[name] = {"anyOf": [field, _NULL]}
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


RESPONSE_SCHEMA = _flat_response_schema()


def _drop_nulls(value: Any) -> Any:
    # The schema sent to the model is flat with every field nullable, so a null object
    # field means "not given". Nulls inside lists are kept and fail validation.
    if isinstance(value, dict):
        return {
            key: _drop_nulls(item) for key, item in value.items() if item is not None
        }
    if isinstance(value, list):
        return [_drop_nulls(item) for item in value]
    return value


def _path(loc: tuple[int | str, ...]) -> str:
    parts = (f"[{part}]" if isinstance(part, int) else f".{part}" for part in loc)
    return "".join(parts).removeprefix(".")


def parse_reply(raw: str) -> ModelResult:
    """Parse raw reply text into the contract. Never repairs; raises InvalidOutput."""
    try:
        data = json.loads(raw)
    except ValueError:
        # `from None`: the original error quotes the reply, which must not reach logs.
        raise InvalidOutput("json") from None
    try:
        return _model_result.validate_python(_drop_nulls(data))
    except ValidationError as error:
        raise InvalidOutput("contract", _path(error.errors()[0]["loc"])) from None
