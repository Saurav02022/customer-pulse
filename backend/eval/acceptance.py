"""Formal acceptance view: per-run pass rule, three-run consistency and the gates.

Everything here is arithmetic over recorded results (AI_EVALUATION.md sections 5, 13
and 14). Nothing calls a model. Semantic values come from the review fields on each
record; where a record has not been reviewed, its pass is provisional.
"""

from __future__ import annotations

from typing import Any

from eval.harness import TRANSIENT, RunRecord

RUNS_PER_CASE = 3
SEEDED_CASES = 12
SYNTHETIC_CASES = 10

# The gate lines, as the plan states them (section 14).
GATES_TEXT = {
    "14.1 structured-output failures (H1, H2)": "0 across all completed results",
    "14.1 grounding-validation failures (H3-H11, H14 reviewed)": "0",
    "14.1 critical trust failures (section 6)": "0",
    "14.2 synthetic per-run passes": "30 / 30",
    "14.3 seeded per-run passes": "at least 35 / 36",
    "14.3 seeded gold state in at least 2 of 3 runs": "every relationship",
    "14.3 the one permitted seeded miss": "semantic only, no hard or critical failure",
    "14.4 transient provider/API failures": "at most 1 in the attempt",
    "14.5 latency and cost": "measured, no threshold yet",
}

SEMANTIC_DIMS = ("G", "C", "N", "R")


def critical_codes(record: RunRecord) -> list[str]:
    """Mechanical and reviewed critical failures together, de-duplicated."""
    return list(dict.fromkeys(record.mechanical_critical + record.critical_flags))


def semantic_zero(record: RunRecord) -> bool:
    return any(record.semantic.get(dim) == 0 for dim in SEMANTIC_DIMS)


def per_run_pass(record: RunRecord) -> bool:
    """Section 5 per-run pass rule: hard checks pass, no critical failure, S is 2 and
    no applicable reviewed dimension is 0."""
    return (
        record.reliability not in TRANSIENT
        and record.hard_validation == "pass"
        and not critical_codes(record)
        and record.state_correct is True
        and not semantic_zero(record)
    )


def three_run_view(records: list[RunRecord]) -> list[dict[str, Any]]:
    """One row per case with the state and pass of each run, in case order."""
    by_case: dict[str, dict[int, RunRecord]] = {}
    order: list[str] = []
    for r in result_slots(records):
        if r.case_id not in by_case:
            order.append(r.case_id)
        by_case.setdefault(r.case_id, {})[r.run] = r
    rows = []
    for case_id in order:
        runs = by_case[case_id]
        first = next(iter(runs.values()))
        states = [runs[n].actual_outcome if n in runs else None for n in (1, 2, 3)]
        passes = [per_run_pass(runs[n]) if n in runs else False for n in (1, 2, 3)]
        rows.append(
            {
                "case_id": case_id,
                "case_type": first.case_type,
                "name": first.name,
                "expected": first.expected_outcome,
                "states": states,
                "passes": passes,
                "expected_state_count": sum(
                    1 for s in states if s == first.expected_outcome
                ),
                "pass_count": sum(passes),
                "critical": sorted(
                    {code for r in runs.values() for code in critical_codes(r)}
                ),
            }
        )
    return rows


def result_slots(records: list[RunRecord]) -> list[RunRecord]:
    """The completed model results, one per (case, run). A transient provider failure
    is not a model result (section 14), so it never fills a slot; if a slot somehow
    holds two completed results, the later one wins."""
    slots: dict[tuple[str, int], RunRecord] = {}
    for r in records:
        if r.reliability not in TRANSIENT:
            slots[(r.case_id, r.run)] = r
    return list(slots.values())


def gates(
    records: list[RunRecord], transients: list[RunRecord] = ()
) -> dict[str, dict[str, Any]]:
    """Every acceptance gate with its target, observed value and verdict.

    `records` are the formal result slots. `transients` are provider-failed attempts
    that the plan (14.4) repeats; they count only toward the reliability gate.
    """
    transient = [r for r in [*records, *transients] if r.reliability in TRANSIENT]
    completed = result_slots(records)
    records = completed
    structured = [
        r
        for r in completed
        if r.structured_output in {"malformed_json", "contract"}
        or r.reliability == "empty_or_blocked"
    ]
    grounding = [r for r in completed if r.grounding not in {"ok", "n/a"}]
    unreviewed_h14 = [
        r for r in completed if r.h14_flags and len(r.h14_review) < len(r.h14_flags)
    ]
    critical = [(r.case_id, r.run, code) for r in records for code in critical_codes(r)]
    reviewed = all(bool(r.semantic) for r in completed if r.hard_validation == "pass")

    rows = three_run_view(records)
    seeded = [row for row in rows if row["case_type"] == "seeded"]
    synthetic = [row for row in rows if row["case_type"] == "synthetic"]
    seeded_passes = sum(row["pass_count"] for row in seeded)
    synthetic_passes = sum(row["pass_count"] for row in synthetic)
    below_two_of_three = [
        row["case_id"] for row in seeded if row["expected_state_count"] < 2
    ]
    seeded_misses = [
        (r.case_id, r.run)
        for r in records
        if r.case_type == "seeded" and not per_run_pass(r)
    ]
    miss_is_semantic_only = all(
        next(
            x for x in records if x.case_id == case_id and x.run == run
        ).hard_validation
        == "pass"
        and not critical_codes(
            next(x for x in records if x.case_id == case_id and x.run == run)
        )
        for case_id, run in seeded_misses
    )
    pending = "human-review pending"

    def verdict(ok: bool) -> str:
        # Semantic review can only turn a pass into a miss, never the reverse, so a
        # line that already fails on mechanical facts is a FAIL before review.
        if not ok:
            return "FAIL"
        return "PASS" if reviewed else pending

    return {
        "14.1 structured-output failures (H1, H2)": {
            "target": "0",
            "observed": len(structured),
            "verdict": "PASS" if not structured else "FAIL",
        },
        "14.1 grounding-validation failures (H3-H11, H14 reviewed)": {
            "target": "0, every H14 flag reviewed",
            "observed": f"{len(grounding)} failures, {len(unreviewed_h14)} unreviewed",
            "verdict": "PASS" if not grounding and not unreviewed_h14 else "FAIL",
        },
        "14.1 critical trust failures (section 6)": {
            "target": "0",
            "observed": len(critical),
            "detail": critical,
            "verdict": verdict(not critical),
        },
        "14.2 synthetic per-run passes": {
            "target": "30 / 30",
            "observed": f"{synthetic_passes} / {SYNTHETIC_CASES * RUNS_PER_CASE}",
            "verdict": verdict(synthetic_passes == SYNTHETIC_CASES * RUNS_PER_CASE),
        },
        "14.3 seeded per-run passes": {
            "target": "at least 35 / 36",
            "observed": f"{seeded_passes} / {SEEDED_CASES * RUNS_PER_CASE}",
            "verdict": verdict(seeded_passes >= 35),
        },
        "14.3 seeded gold state in at least 2 of 3 runs": {
            "target": "every relationship",
            "observed": f"{len(seeded) - len(below_two_of_three)} of {len(seeded)}",
            "detail": below_two_of_three,
            "verdict": verdict(not below_two_of_three),
        },
        "14.3 the one permitted seeded miss": {
            "target": "semantic only (no hard or critical failure)",
            "observed": f"{len(seeded_misses)} miss(es): {seeded_misses}",
            "verdict": verdict(len(seeded_misses) <= 1 and miss_is_semantic_only),
        },
        "14.4 transient provider/API failures": {
            "target": "at most 1",
            "observed": len(transient),
            "verdict": "PASS" if len(transient) <= 1 else "FAIL",
        },
        "completed results": {
            "target": str(
                SEEDED_CASES * RUNS_PER_CASE + SYNTHETIC_CASES * RUNS_PER_CASE
            ),
            "observed": len(completed),
            "verdict": "PASS" if len(completed) == 66 else "FAIL",
        },
    }


def accounting(
    records: list[RunRecord], transients: list[RunRecord] = ()
) -> dict[str, Any]:
    """Keep the four counts apart: result slots, formal invocations, provider attempts
    (including the provider's own internal retries) and transient failures."""
    invocations = [*records, *transients]
    attempts = sum(r.provider_attempts or 1 for r in invocations)
    failed = [r for r in invocations if r.reliability in TRANSIENT]
    return {
        "result_slots": len(result_slots(records)),
        "formal_invocations": len(invocations),
        "provider_attempts": attempts,
        "internal_retries": attempts - len(invocations),
        "transient_failures": [
            {"case_id": r.case_id, "run": r.run, "cause": r.reliability} for r in failed
        ],
    }


def all_gates_pass(gate_table: dict[str, dict[str, Any]]) -> bool:
    return all(row["verdict"] == "PASS" for row in gate_table.values())
