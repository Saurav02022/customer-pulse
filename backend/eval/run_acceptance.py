"""Formal acceptance run: every case once in each of three independent runs.

Manual only. Run from ``backend/`` with the owner's key in ``backend/.env``:

    python -m eval.run_acceptance

Run 1 walks all 22 cases, then run 2, then run 3. Each case invocation is a fresh model
call through the production pipeline with no cache and no database. A transient
provider failure is recorded apart and that case run is repeated once, as section 14.4
of the plan prescribes, so the attempt still has 66 completed results. Nothing else is
ever repeated. Artifacts go to a new ``.context/evaluations/acceptance-<version>-*``
directory; earlier artifacts are never touched.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.assessment.gemini import GeminiAssessmentProvider
from app.assessment.prompt import PROMPT_VERSION
from app.settings import Settings
from eval.acceptance import GATES_TEXT, RUNS_PER_CASE, accounting, gates
from eval.acceptance_report import to_acceptance_markdown
from eval.cases import load_cases
from eval.harness import TRANSIENT, RunRecord, run_case
from eval.report import run_metadata, to_json

EXPECTED_VERSION = "assessment-v3"
EXPECTED_MODEL = "gemini-3.8-flash"
EXPECTED_CASES = 22
OUTPUT_ROOT = Path(__file__).resolve().parents[2] / ".context" / "evaluations"


def _freeze_check(provider: GeminiAssessmentProvider, case_count: int) -> None:
    problems = []
    if PROMPT_VERSION != EXPECTED_VERSION:
        problems.append(f"prompt version is {PROMPT_VERSION}, not {EXPECTED_VERSION}")
    if provider.model != EXPECTED_MODEL:
        problems.append(f"model is {provider.model}, not {EXPECTED_MODEL}")
    if provider.name != "gemini":
        problems.append(f"provider is {provider.name}, not gemini")
    if case_count != EXPECTED_CASES:
        problems.append(f"{case_count} cases loaded, expected {EXPECTED_CASES}")
    if problems:
        raise SystemExit("STOP: " + "; ".join(problems))


async def _run() -> int:
    cases = load_cases()
    settings = Settings()
    provider = GeminiAssessmentProvider(settings)
    _freeze_check(provider, len(cases))
    meta = run_metadata(provider)
    meta["runs_per_case"] = RUNS_PER_CASE
    meta["gates"] = GATES_TEXT

    planned = len(cases) * RUNS_PER_CASE
    print("=== Formal acceptance — planned run ===")
    print(f"cases            : {len(cases)} (12 seeded + 10 synthetic)")
    print(f"runs per case    : {RUNS_PER_CASE}")
    print(f"planned results  : {planned}")
    print(f"provider         : {provider.name}")
    print(f"model            : {provider.model}")
    print(f"prompt version   : {meta['prompt_version']}")
    print(f"prompt sha       : {meta['prompt_sha'][:16]}…")
    print("=======================================")

    records: list[RunRecord] = []
    transients: list[RunRecord] = []
    try:
        for run in range(1, RUNS_PER_CASE + 1):
            print(f"\n--- run {run} of {RUNS_PER_CASE} ---")
            for index, case in enumerate(cases, start=1):
                record = await run_case(provider, case)
                record.run = run
                if record.reliability in TRANSIENT:
                    # Section 14.4: recorded apart, then this case run is repeated once.
                    transients.append(record)
                    print(
                        f"[R{run} {index:2d}/{len(cases)}] {case.case_id}: "
                        f"{record.reliability} — repeating once (14.4)",
                        flush=True,
                    )
                    record = await run_case(provider, case)
                    record.run = run
                records.append(record)
                print(
                    f"[R{run} {index:2d}/{len(cases)}] {case.case_id:8} "
                    f"expected={record.expected_outcome:22} "
                    f"actual={str(record.actual_outcome or record.reliability):22} "
                    f"{'S=2' if record.state_correct else 'S=0'} "
                    f"hard={record.hard_validation} h14={len(record.h14_flags)} "
                    f"attempts={record.provider_attempts} ms={record.latency_ms}",
                    flush=True,
                )
    finally:
        await provider.aclose()

    counts = accounting(records, transients)
    meta.update(counts)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUTPUT_ROOT / f"acceptance-{meta['prompt_version']}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = to_json(meta, records)
    # The harness aggregate sees only result slots; transient counts come from here.
    payload["aggregate"]["transient_failures"] = len(counts["transient_failures"])
    payload["transient_results"] = to_json(meta, transients)["records"]
    payload["gates"] = gates(records, transients)
    (out_dir / "acceptance.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "acceptance.md").write_text(
        to_acceptance_markdown(meta, records, transients), encoding="utf-8"
    )

    print("\n=== Gates (mechanical; semantic review pending) ===")
    for name, row in gates(records, transients).items():
        print(
            f"{name}: target={row['target']} observed={row['observed']} "
            f"-> {row['verdict']}"
        )
    print(
        f"\nresult slots={counts['result_slots']} "
        f"formal invocations={counts['formal_invocations']} "
        f"provider attempts={counts['provider_attempts']} "
        f"internal retries={counts['internal_retries']} "
        f"transient failures={len(counts['transient_failures'])}"
    )
    print(f"artifacts written to: {out_dir}")
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
