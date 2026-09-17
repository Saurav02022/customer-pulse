"""Markdown for a formal acceptance run: gates, three-run view, review material."""

from __future__ import annotations

from typing import Any

from eval.acceptance import (
    GATES_TEXT,
    critical_codes,
    gates,
    per_run_pass,
    result_slots,
    three_run_view,
)
from eval.harness import RunRecord


def _claim(result: dict[str, Any] | None, field: str) -> str:
    if not result or result.get(field) in (None, []):
        return "—"
    claim = result[field]
    if isinstance(claim, list):
        return " | ".join(
            f"{i['text']} [contacts={','.join(i['contacts'])}; "
            f"evidence={','.join(i['evidence'])}]"
            for i in claim
        )
    return f"{claim['text']} [evidence={','.join(claim['evidence'])}]"


def _state_cell(record: RunRecord | None) -> str:
    if record is None:
        return "—"
    if record.reliability != "ok":
        return f"({record.reliability})"
    if record.hard_validation != "pass":
        return f"({record.hard_validation})"
    return record.actual_outcome or "—"


def to_acceptance_markdown(
    meta: dict[str, Any],
    records: list[RunRecord],
    transients: list[RunRecord] = (),
) -> str:
    records = result_slots(records)
    lines: list[str] = []
    lines.append(f"# Formal acceptance — prompt {meta['prompt_version']}")
    lines.append("")
    lines.append(
        f"- timestamp: {meta['timestamp']} · provider: {meta['provider']} · "
        f"model: {meta['model']} · prompt_sha: {meta['prompt_sha'][:12]}… · "
        f"eval_set: {meta['eval_set_version']} · runs_per_case: {meta['runs_per_case']}"
    )
    lines.append("")
    lines.append("## Gate lines (AI_EVALUATION.md section 14)")
    for name, target in GATES_TEXT.items():
        lines.append(f"- {name}: {target}")
    lines.append("")

    lines.append("## Threshold table")
    lines.append("")
    lines.append("| gate | target | observed | verdict |")
    lines.append("|---|---|---|---|")
    for name, row in gates(records, transients).items():
        detail = f" {row['detail']}" if row.get("detail") else ""
        lines.append(
            f"| {name} | {row['target']} | {row['observed']}{detail} | "
            f"{row['verdict']} |"
        )
    lines.append("")

    rows = three_run_view(records)
    lines.append("## Three-run consistency — seeded")
    lines.append("")
    lines.append("| case | expected | R1 | R2 | R3 | state /3 | passes /3 | critical |")
    lines.append("|---|---|---|---|---|---|---|---|")
    by_run = {(r.case_id, r.run): r for r in records}
    for row in rows:
        if row["case_type"] != "seeded":
            continue
        cells = [_state_cell(by_run.get((row["case_id"], n))) for n in (1, 2, 3)]
        lines.append(
            f"| {row['case_id']} {row['name']} | {row['expected']} | "
            f"{cells[0]} | {cells[1]} | {cells[2]} | "
            f"{row['expected_state_count']} | {row['pass_count']} | "
            f"{','.join(row['critical']) or '—'} |"
        )
    lines.append("")
    lines.append("## Three-run consistency — synthetic")
    lines.append("")
    lines.append("| case | expected | R1 | R2 | R3 | passes /3 | critical |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in rows:
        if row["case_type"] != "synthetic":
            continue
        cells = []
        for n in (1, 2, 3):
            r = by_run.get((row["case_id"], n))
            cell = _state_cell(r)
            cells.append(f"{cell} {'✓' if r and per_run_pass(r) else '✗'}")
        lines.append(
            f"| {row['case_id']} | {row['expected']} | {cells[0]} | {cells[1]} | "
            f"{cells[2]} | {row['pass_count']} | {','.join(row['critical']) or '—'} |"
        )
    lines.append("")

    lines.append("## H14 flags and review decisions")
    lines.append("")
    any_flag = False
    for r in records:
        for index, flag in enumerate(r.h14_flags):
            any_flag = True
            decision = (
                r.h14_review[index] if index < len(r.h14_review) else "UNREVIEWED"
            )
            lines.append(
                f"- {r.case_id} R{r.run} [{flag['path']}] ({flag['order_words']}): "
                f"“{flag['text']}” → {decision}"
            )
    if not any_flag:
        lines.append("- none")
    lines.append("")

    lines.append("## Per-case review material")
    lines.append("")
    for row in rows:
        lines.append(
            f"### {row['case_id']} — {row['name']} (expected {row['expected']})"
        )
        for n in (1, 2, 3):
            r = by_run.get((row["case_id"], n))
            if r is None:
                lines.append(f"- R{n}: missing")
                continue
            lines.append(
                f"- **R{n}** actual={r.actual_outcome or r.reliability} · "
                f"S={'2' if r.state_correct else '0'} · hard={r.hard_validation} · "
                f"pass={'yes' if per_run_pass(r) else 'no'} · "
                f"critical={','.join(critical_codes(r)) or '—'} · "
                f"semantic={r.semantic or 'pending'} · latency_ms={r.latency_ms}"
            )
            if r.trusted_result and r.actual_outcome != "insufficient_evidence":
                t = r.trusted_result
                lines.append(f"  - reason: {_claim(t, 'reason')}")
                lines.append(f"  - summary: {_claim(t, 'summary')}")
                if t.get("waiting_for"):
                    lines.append(f"  - waiting_for: {_claim(t, 'waiting_for')}")
                if t.get("next_action"):
                    lines.append(f"  - next_action: {_claim(t, 'next_action')}")
                lines.append(f"  - open_items: {_claim(t, 'open_items')}")
        lines.append("")
    return "\n".join(lines)
