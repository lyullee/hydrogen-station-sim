import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research" / "grune_2014_public_pressure_trace_recheck_2026_10_12.json"
REPORT = ROOT / "research" / "GRUNE_2014_PUBLIC_PRESSURE_TRACE_RECHECK_2026_10_12.md"


def test_grune_recheck_preserves_missing_trace_boundary():
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["status"] == "NO_NEW_MACHINE_READABLE_FULL_TRACE_FOUND"
    assert record["findings"]["machine_readable_full_pressure_trace_found"] is False
    assert record["findings"]["rights_cleared_raw_archive_found"] is False
    assert record["existing_trace"]["gate_status"] == "PENDING_INELIGIBLE_FOR_JOINT_SCREEN"
    assert record["decision"]["promote_to_independent_validation"] is False
    assert record["decision"]["runtime_change"] is False
    assert record["decision"]["readiness_gate_effect"] == "none"


def test_grune_recheck_report_states_the_reentry_condition():
    report = REPORT.read_text(encoding="utf-8")
    assert "complete machine-readable pressure trace" in report
    assert "required half-pressure crossing" in report
    assert "runtime model, gate thresholds and manuscript claims are unchanged" in report
