import json
from pathlib import Path

from scripts.summarize_hiad_hrs_evidence import build_summary


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/public_validation/raw/hiad_2_2/HIAD 2.2.xlsx"


def test_hiad_public_evidence_summary_is_traceable_and_not_a_blinded_casebook():
    summary = build_summary(SOURCE)
    assert summary["source"]["sha256"]
    assert summary["selection"]["coordinator_approval"] is False
    assert summary["selection"]["blinded_response_text_excluded"] is True
    assert summary["aggregate"]["case_count"] == 34
    assert summary["aggregate"]["with_emergency_action"] == 29
    assert summary["aggregate"]["with_lesson_learnt"] == 24
    assert summary["aggregate"]["with_corrective_measures"] == 25
    assert {case["event_id"] for case in summary["cases"]} >= {"401", "702", "884", "1198"}
    assert all("emergency_action" not in case for case in summary["cases"])


def test_committed_hiad_public_evidence_matches_source():
    record = json.loads((ROOT / "research/hiad_hrs_public_evidence.json").read_text(encoding="utf-8"))
    fresh = build_summary(SOURCE)
    assert record["source"]["sha256"] == fresh["source"]["sha256"]
    assert record["aggregate"] == fresh["aggregate"]
    assert [case["event_id"] for case in record["cases"]] == [case["event_id"] for case in fresh["cases"]]

