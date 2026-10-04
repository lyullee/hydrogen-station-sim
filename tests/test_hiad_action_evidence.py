import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hiad_action_evidence_is_derived_and_non_evaluative():
    report = json.loads((ROOT / "research/hiad_action_evidence.json").read_text(encoding="utf-8"))
    assert report["status"] == "derived_non_evaluative_action_taxonomy"
    assert report["evidence_role"] == "public_incident_grounding_summary"
    assert report["case_count"] == 34
    assert report["source"]["raw_text_retained"] is False
    assert report["source"]["holdout_use"] is False
    assert report["taxonomy"]["field_presence_counts"]["emergency_action"] > 0
    assert report["taxonomy"]["category_counts"]["shutdown_isolation_depressurization"] > 0
    assert report["taxonomy"]["category_counts"]["inspection_leak_test_repair"] > 0
    assert all("emergency_action" not in case for case in report["cases"])
