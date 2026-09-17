"""Targeted real-Gemini regression: the 10 cases that guard the prompt-v2 correction.

Manual only. Run from ``backend/`` with the owner's key in ``backend/.env``:

    python -m eval.run_targeted

It runs exactly the 10 named cases once each, through the production pipeline (no cache,
no database), and writes its own artifacts under ``.context/evaluations/targeted-*`` so
the baseline artifacts are never overwritten.
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

# Default targeted set. Pass case ids on the command line to run a different set. The
# set covers the fixed states plus the same-date, injection and decline guards.
DEFAULT_TARGET_IDS = [
    "cust_010",
    "cust_007",
    "IE-5",
    "CHR-1",
    "cust_009",
    "cust_004",
    "cust_011",
    "IE-3",
    "INJ-4",
    "INJ-1",
]
OUTPUT_ROOT = Path(__file__).resolve().parents[2] / ".context" / "evaluations"


def _targeted_cases(target_ids: list[str]) -> list:
    by_id = {c.case_id: c for c in load_cases()}
    missing = [cid for cid in target_ids if cid not in by_id]
    if missing:
        raise SystemExit(f"STOP: unknown case ids {missing}")
    if len(target_ids) != 10:
        raise SystemExit(f"STOP: expected 10 targeted cases, got {len(target_ids)}")
    return [by_id[cid] for cid in target_ids]


async def _run(target_ids: list[str]) -> int:
    cases = _targeted_cases(target_ids)
    settings = Settings()
    provider = GeminiAssessmentProvider(settings)

    print("=== Real Gemini targeted regression — planned run ===")
    print(f"planned cases  : {len(cases)}")
    print("runs per case  : 1")
    print(f"provider       : {provider.name}")
    print(f"model          : {provider.model}")
    print(f"prompt version : {run_metadata(provider)['prompt_version']}")
    print("case ids       :", ", ".join(c.case_id for c in cases))
    print("=====================================================")

    records: list[RunRecord] = []
    try:
        for index, case in enumerate(cases, start=1):
            print(f"[{index:2d}/{len(cases)}] {case.case_id} …", flush=True)
            record = await run_case(provider, case)
            ok = record.state_correct is True
            print(
                f"        expected={record.expected_outcome} "
                f"actual={record.actual_outcome} "
                f"{'PASS' if ok else 'FAIL'}  reliability={record.reliability} "
                f"structured={record.structured_output} grounding={record.grounding} "
                f"attempts={record.provider_attempts} latency_ms={record.latency_ms}",
                flush=True,
            )
            records.append(record)
    finally:
        await provider.aclose()

    meta = run_metadata(provider)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUTPUT_ROOT / f"targeted-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "targeted.json").write_text(
        json.dumps(to_json(meta, records), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    version = meta["prompt_version"]
    title = f"Real Gemini assessment — targeted regression (prompt {version})"
    (out_dir / "targeted.md").write_text(
        to_markdown(meta, records, title=title), encoding="utf-8"
    )

    agg = aggregate(records)
    print("\n=== Summary ===")
    for key, value in agg.items():
        print(f"{key}: {value}")
    print(f"\nartifacts written to: {out_dir}")
    return 0


def main() -> int:
    target_ids = sys.argv[1:] or DEFAULT_TARGET_IDS
    return asyncio.run(_run(target_ids))


if __name__ == "__main__":
    sys.exit(main())
