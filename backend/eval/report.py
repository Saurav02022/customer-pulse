"""Serialize evaluation records to a JSON artifact and a readable Markdown summary.

No artifact ever holds a secret: only run metadata (provider, model, prompt version and
sha, set version, timestamp), the case facts, the trusted parsed result and the
mechanical flags. The API key, environment values and raw SDK objects never reach here.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from app.assessment.contract import RESPONSE_SCHEMA
from app.assessment.model_input import canonical_json
from app.assessment.prompt import PROMPT_VERSION, SYSTEM_INSTRUCTION
from app.assessment.provider import AssessmentProvider
from eval.cases import EVAL_SET_VERSION
from eval.harness import RunRecord, aggregate

# The only fields an artifact record may carry. A stray secret would need a new field,
# so the offline test asserts records stay within this set.
ALLOWED_RECORD_FIELDS = set(RunRecord.__dataclass_fields__)
ALLOWED_META_FIELDS = {
    "timestamp",
    "provider",
    "model",
    "prompt_version",
    "prompt_sha",
    "eval_set_version",
    "runs_per_case",
}


def prompt_sha() -> str:
    return hashlib.sha256(
        (SYSTEM_INSTRUCTION + canonical_json(RESPONSE_SCHEMA)).encode()
    ).hexdigest()


def run_metadata(provider: AssessmentProvider) -> dict[str, str | int]:
    return {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "provider": provider.name,
        "model": provider.model,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha": prompt_sha(),
        "eval_set_version": EVAL_SET_VERSION,
        "runs_per_case": 1,
    }


def to_json(meta: dict[str, Any], records: list[RunRecord]) -> dict[str, Any]:
    return {
        "meta": meta,
        "aggregate": aggregate(records),
        "records": [asdict(record) for record in records],
    }


def _claim_line(result: dict[str, Any] | None, field: str) -> str:
    if not result or result.get(field) in (None, []):
        return "—"
    claim = result[field]
    if isinstance(claim, list):  # open_items
        return " | ".join(
            f"{item['text']} [contacts={','.join(item['contacts'])}; "
            f"evidence={','.join(item['evidence'])}]"
            for item in claim
        )
    return f"{claim['text']} [evidence={','.join(claim['evidence'])}]"


def to_markdown(
    meta: dict[str, Any],
    records: list[RunRecord],
    title: str = "Real Gemini assessment — baseline (single pass)",
) -> str:
    agg = aggregate(records)
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(
        f"- timestamp: {meta['timestamp']}  ·  provider: {meta['provider']}  ·  "
        f"model: {meta['model']}"
    )
    lines.append(
        f"- prompt_version: {meta['prompt_version']}  ·  prompt_sha: "
        f"{meta['prompt_sha'][:12]}…  ·  eval_set: {meta['eval_set_version']}  ·  "
        f"runs_per_case: {meta['runs_per_case']}"
    )
    lines.append("")
    lines.append("## Aggregate")
    for key, value in agg.items():
        lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Per-case (mechanical + material for human review)")
    lines.append("")
    header = (
        "| case | type | expected | actual | S | reliability | structured | "
        "grounding | hard | H14 | mech CF | attempts | latency ms |"
    )
    lines.append(header)
    lines.append("|" + "---|" * 13)
    for r in records:
        s = "" if r.state_correct is None else ("2" if r.state_correct else "0")
        h14 = str(len(r.h14_flags)) if r.h14_flags else "0"
        cf = ",".join(r.mechanical_critical) or "—"
        lines.append(
            f"| {r.case_id} | {r.case_type} | {r.expected_outcome} | "
            f"{r.actual_outcome or '—'} | {s} | {r.reliability} | "
            f"{r.structured_output} | {r.grounding} | {r.hard_validation} | {h14} | "
            f"{cf} | {r.provider_attempts or '—'} | {r.latency_ms or '—'} |"
        )
    lines.append("")

    lines.append("## Human-review material (semantic dimensions are provisional)")
    lines.append("")
    for r in records:
        lines.append(f"### {r.case_id} — {r.name}")
        lines.append(
            f"- expected: {r.expected_outcome}  ·  actual: {r.actual_outcome or '—'}"
            f"  ·  state correct: {r.state_correct}"
        )
        lines.append(f"- note: {r.note}")
        if r.reliability != "ok":
            lines.append(
                f"- reliability outcome: **{r.reliability}** (no trusted result)"
            )
        elif r.hard_validation != "pass":
            lines.append(
                f"- hard-validation failure: **{r.hard_validation}** "
                f"(structured={r.structured_output}, grounding={r.grounding})"
            )
        else:
            result = r.trusted_result
            lines.append(f"- reason: {_claim_line(result, 'reason')}")
            lines.append(f"- summary: {_claim_line(result, 'summary')}")
            lines.append(f"- waiting_for: {_claim_line(result, 'waiting_for')}")
            lines.append(f"- next_action: {_claim_line(result, 'next_action')}")
            lines.append(f"- open_items: {_claim_line(result, 'open_items')}")
            if r.h14_flags:
                for flag in r.h14_flags:
                    lines.append(
                        f"- H14 flag [{flag['path']}] order words "
                        f"({flag['order_words']}): {flag['text']}"
                    )
            if r.mechanical_critical:
                lines.append(
                    f"- mechanical critical: {', '.join(r.mechanical_critical)}"
                )
            lines.append("- provisional semantic (G/C/N/R): pending human review")
        lines.append("")
    return "\n".join(lines)
