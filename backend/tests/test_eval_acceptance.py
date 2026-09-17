"""Offline tests for the acceptance arithmetic: per-run pass rule, three-run view and
gates. No model is called; records are built by hand."""

from eval.acceptance import (
    GATES_TEXT,
    accounting,
    all_gates_pass,
    gates,
    per_run_pass,
    three_run_view,
)
from eval.acceptance_report import to_acceptance_markdown
from eval.harness import RunRecord


def _record(
    case_id: str,
    case_type: str,
    expected: str,
    actual: str | None,
    run: int,
    **changes,
) -> RunRecord:
    ok = actual is not None
    fields = {
        "case_id": case_id,
        "case_type": case_type,
        "name": case_id,
        "expected_outcome": expected,
        "reliability": "ok" if ok else "provider_timeout",
        "structured_output": "ok" if ok else "n/a",
        "grounding": "ok" if ok else "n/a",
        "actual_outcome": actual,
        "state_correct": (actual == expected) if ok else None,
        "hard_validation": "pass" if ok else "n/a",
        "run": run,
        "semantic": {"G": 2, "C": 2, "N": 2, "R": 2} if ok else {},
    }
    fields.update(changes)
    return RunRecord(**fields)


def _clean_attempt() -> list[RunRecord]:
    seeded = [f"cust_{n:03d}" for n in range(1, 13)]
    synthetic = [f"SYN-{n}" for n in range(1, 11)]
    records = []
    for run in (1, 2, 3):
        records += [_record(c, "seeded", "waiting", "waiting", run) for c in seeded]
        records += [
            _record(c, "synthetic", "action_needed", "action_needed", run)
            for c in synthetic
        ]
    return records


def test_per_run_pass_needs_state_hard_checks_and_no_zero() -> None:
    good = _record("cust_001", "seeded", "waiting", "waiting", 1)
    assert per_run_pass(good)
    assert not per_run_pass(
        _record("cust_001", "seeded", "waiting", "action_needed", 1)
    )
    assert not per_run_pass(
        _record("cust_001", "seeded", "waiting", "waiting", 1, critical_flags=["CF6"])
    )
    assert not per_run_pass(
        _record("cust_001", "seeded", "waiting", "waiting", 1, semantic={"R": 0})
    )
    assert not per_run_pass(_record("cust_001", "seeded", "waiting", None, 1))


def test_three_run_view_counts_states_and_passes() -> None:
    records = [
        _record("cust_007", "seeded", "action_needed", "action_needed", 1),
        _record("cust_007", "seeded", "action_needed", "insufficient_evidence", 2),
        _record("cust_007", "seeded", "action_needed", "action_needed", 3),
    ]
    [row] = three_run_view(records)
    assert row["states"] == ["action_needed", "insufficient_evidence", "action_needed"]
    assert row["expected_state_count"] == 2
    assert row["pass_count"] == 2


def test_clean_attempt_passes_every_gate() -> None:
    table = gates(_clean_attempt())
    assert set(table) >= set(GATES_TEXT) - {"14.5 latency and cost"}
    assert all_gates_pass(table)
    assert table["14.2 synthetic per-run passes"]["observed"] == "30 / 30"
    assert table["14.3 seeded per-run passes"]["observed"] == "36 / 36"


def test_one_semantic_seeded_miss_is_allowed_but_two_are_not() -> None:
    records = _clean_attempt()
    records[0] = _record("cust_001", "seeded", "waiting", "action_needed", 1)
    table = gates(records)
    assert table["14.3 seeded per-run passes"]["verdict"] == "PASS"
    assert table["14.3 the one permitted seeded miss"]["verdict"] == "PASS"
    assert table["14.3 seeded gold state in at least 2 of 3 runs"]["verdict"] == "PASS"
    records[22] = _record("cust_001", "seeded", "waiting", "action_needed", 2)
    table = gates(records)
    assert table["14.3 seeded per-run passes"]["verdict"] == "FAIL"
    assert table["14.3 seeded gold state in at least 2 of 3 runs"]["verdict"] == "FAIL"
    assert not all_gates_pass(table)


def test_a_critical_failure_fails_the_attempt_even_with_the_right_state() -> None:
    records = _clean_attempt()
    records[5] = _record(
        "cust_006", "seeded", "waiting", "waiting", 1, critical_flags=["CF8"]
    )
    table = gates(records)
    assert table["14.1 critical trust failures (section 6)"]["verdict"] == "FAIL"
    assert table["14.3 the one permitted seeded miss"]["verdict"] == "FAIL"


def test_unreviewed_h14_flag_fails_the_grounding_gate() -> None:
    records = _clean_attempt()
    records[3] = _record(
        "cust_004",
        "seeded",
        "waiting",
        "waiting",
        1,
        h14_flags=[{"path": "reason", "order_words": "after", "text": "x after y"}],
    )
    key = "14.1 grounding-validation failures (H3-H11, H14 reviewed)"
    assert gates(records)[key]["verdict"] == "FAIL"
    records[3].h14_review = ["supported: names the awaited event"]
    assert all_gates_pass(gates(records))


def test_transient_failures_are_counted_apart() -> None:
    records = _clean_attempt() + [
        _record("cust_002", "seeded", "action_needed", None, 2)
    ]
    table = gates(records)
    assert table["14.4 transient provider/API failures"]["observed"] == 1
    assert table["14.4 transient provider/API failures"]["verdict"] == "PASS"
    records.append(_record("cust_003", "seeded", "action_needed", None, 3))
    assert gates(records)["14.4 transient provider/API failures"]["verdict"] == "FAIL"


# --- timeout then repeat (formal run: cust_007 R3 timed out, then was repeated) -------


def _timeout_then_repeat() -> tuple[list[RunRecord], list[RunRecord]]:
    """The 66 result slots, where cust_007 declined in R1 and R3, plus the one
    timed-out attempt that the plan repeated. The timeout used both provider tries."""
    records = []
    for r in _clean_attempt():
        if r.case_id == "cust_007" and r.run in (1, 3):
            r = _record("cust_007", "seeded", "waiting", "insufficient_evidence", r.run)
        r.provider_attempts = 2 if (r.case_id, r.run) == ("cust_007", 3) else 1
        records.append(r)
    timeout = _record("cust_007", "seeded", "waiting", None, 3, provider_attempts=2)
    return records, [timeout]


def test_timeout_repeat_keeps_the_four_counts_apart() -> None:
    records, transients = _timeout_then_repeat()
    counts = accounting(records, transients)
    assert counts["result_slots"] == 66
    assert counts["formal_invocations"] == 67
    assert counts["provider_attempts"] == 69
    assert counts["internal_retries"] == 2
    assert counts["transient_failures"] == [
        {"case_id": "cust_007", "run": 3, "cause": "provider_timeout"}
    ]


def test_timeout_repeat_counts_the_transient_once_and_each_miss_once() -> None:
    records, transients = _timeout_then_repeat()
    table = gates(records, transients)
    assert table["14.4 transient provider/API failures"]["observed"] == 1
    assert table["14.4 transient provider/API failures"]["verdict"] == "PASS"
    assert table["completed results"]["observed"] == 66
    misses = table["14.3 the one permitted seeded miss"]["observed"]
    assert misses == "2 miss(es): [('cust_007', 1), ('cust_007', 3)]"
    assert table["14.3 seeded per-run passes"]["observed"] == "34 / 36"


def test_a_transient_attempt_mixed_into_the_results_never_fills_a_slot() -> None:
    # Passing the failed attempt with the results (the earlier bug) gives the same
    # answer: it is not a model result and is not a second cust_007 R3.
    records, transients = _timeout_then_repeat()
    mixed = gates(transients + records)
    assert mixed == gates(records, transients)
    [row] = [
        r for r in three_run_view(transients + records) if r["case_id"] == "cust_007"
    ]
    assert row["states"] == [
        "insufficient_evidence",
        "waiting",
        "insufficient_evidence",
    ]


def test_mechanical_failures_are_fail_before_semantic_review() -> None:
    records, transients = _timeout_then_repeat()
    for r in records:
        r.semantic = {}
    table = gates(records, transients)
    assert table["14.3 seeded per-run passes"]["verdict"] == "FAIL"
    assert table["14.3 seeded gold state in at least 2 of 3 runs"]["verdict"] == "FAIL"
    # A line that passes mechanically still waits for review.
    assert table["14.2 synthetic per-run passes"]["verdict"] == "human-review pending"


def test_markdown_lists_each_result_slot_once() -> None:
    records, transients = _timeout_then_repeat()
    meta = {
        "timestamp": "t",
        "provider": "fake",
        "model": "m",
        "prompt_sha": "0" * 64,
        "prompt_version": "v",
        "eval_set_version": "e",
        "runs_per_case": 3,
    }
    text = to_acceptance_markdown(meta, transients + records, transients)
    assert text.count("### cust_007") == 1
    assert text.count("- **R3** actual=") == 22
    assert "(provider_timeout)" not in text
