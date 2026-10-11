import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research" / "usn_17932439_pressure_peaking_recheck_2026_10_11.json"


def test_usn_pressure_peaking_recheck_is_complete_and_bounded():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert data["status"] == "completed_post_access_pressure_peaking_recheck"
    assert data["source"]["doi"] == "10.23642/USN.17932439"
    assert data["source"]["license"] == "CC BY 4.0"
    assert len(data["source"]["file_manifest"]) == 10
    assert data["aggregate"]["eligible_case_count"] == 10
    assert data["aggregate"]["excluded_case_count"] == 0
    assert data["aggregate"]["joint_primary_pass_count"] == 8
    assert data["aggregate"]["interpretation"] == "diagnostic_only"
    assert "not an independent confirmatory holdout" in data["claim_boundary"]


def test_usn_pressure_peaking_recheck_has_no_runtime_promotion():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert data["model"]["parameter_fitting"] is False
    assert "station control" in data["claim_boundary"]
    assert all(len(row["source_file"]) > 0 for row in data["cases"])
