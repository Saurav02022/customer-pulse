"""Run the real-Gemini baseline: every case once, through the production pipeline.

Manual only. Run from ``backend/`` with the owner's key in ``backend/.env``:

    python -m eval.run_baseline

It makes exactly one model call per case (the provider keeps its own one internal retry
for a transient failure). It never prints the key, never touches the product database,
and writes a JSON artifact and a Markdown summary under ``.context/evaluations/`` (an
ignored, local-only location).
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.assessment.gemini import GeminiAssessmentProvider
from app.settings import Settings
from eval.cases import load_cases
from eval.harness import RunRecord, aggregate, run_case
from eval.report import run_metadata, to_json, to_markdown

EXPECTED_CASE_COUNT = 22
OUTPUT_ROOT = Path(__file__).resolve().parents[2] / ".context" / "evaluations"


def _confirm_counts(cases: list) -> None:
    seeded = sum(1 for c in cases if c.case_type == "seeded")
    synthetic = sum(1 for c in cases if c.case_type == "synthetic")
    if len(cases) != EXPECTED_CASE_COUNT or seeded != 12 or synthetic != 10:
        raise SystemExit(
            f"STOP: expected 22 cases (12 seeded + 10 synthetic), got {len(cases)} "
            f"({seeded} seeded + {synthetic} synthetic). "
            "Check AI_EVALUATION.md and cases.py."
        )


async def _run() -> int:
    cases = load_cases()
    _confirm_counts(cases)

    settings = Settings()
    provider = GeminiAssessmentProvider(settings)  # refuses to start without a key

    # Cost control: announce the plan. Never the key.
    print("=== Real Gemini baseline — planned run ===")
    print(f"planned evaluation cases : {len(cases)} (12 seeded + 10 synthetic)")
    print("runs per case            : 1")
    print(f"provider                 : {provider.name}")
    print(f"model                    : {provider.model}")
    print(f"prompt version           : {run_metadata(provider)['prompt_version']}")
    print("case ids                 :", ", ".join(c.case_id for c in cases))
    print("==========================================")

    records: list[RunRecord] = []
    try:
        for index, case in enumerate(cases, start=1):
            print(
                f"[{index:2d}/{len(cases)}] {case.case_id} ({case.case_type}) …",
                flush=True,
            )
            record = await run_case(provider, case)
            print(
                f"        reliability={record.reliability} "
                f"structured={record.structured_output} grounding={record.grounding} "
                f"actual={record.actual_outcome} attempts={record.provider_attempts} "
                f"latency_ms={record.latency_ms}",
                flush=True,
            )
            records.append(record)
    finally:
        await provider.aclose()

    meta = run_metadata(provider)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUTPUT_ROOT / f"baseline-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "baseline.json").write_text(
        json.dumps(to_json(meta, records), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (out_dir / "baseline.md").write_text(to_markdown(meta, records), encoding="utf-8")

    agg = aggregate(records)
    print("\n=== Summary ===")
    for key, value in agg.items():
        print(f"{key}: {value}")
    print(f"\nartifacts written to: {out_dir}")
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
