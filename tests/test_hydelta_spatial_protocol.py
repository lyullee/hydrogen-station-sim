import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/hydelta_indoor_spatial_holdout_protocol_2026_10_08.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hydelta_protocol_freezes_candidate_before_report_access():
    record = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert record["status"] == "FROZEN_BEFORE_REPORT_FILE_ACCESS"
    assert record["source"]["doi"] == "10.5281/zenodo.8154318"
    assert record["pre_access_disclosure"]["report_file_downloaded"] is False
    assert record["pre_access_disclosure"]["exact_per_sensor_outcomes_known_before_freeze"] is False
    candidate = record["locked_candidate"]
    assert candidate["implementation_sha256"] == _sha256(
        ROOT / candidate["implementation"]
    )
    assert candidate["development_artifact_sha256"] == _sha256(
        ROOT / candidate["development_artifact"]
    )
    assert candidate["formula_change_permitted_after_report_access"] is False
    assert candidate["runtime_application_before_holdout_pass"] is False


def test_hydelta_protocol_rejects_aggregate_or_figure_only_rescue():
    record = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    eligibility = record["eligibility"]
    assert eligibility["minimum_hydrogen_experiments"] >= 4
    assert eligibility["requires_per_sensor_numeric_response"] is True
    assert any("color" in value for value in eligibility["prohibited_response"])
    assert "do not digitize figures" in eligibility["ineligible_decision"]
    assert any(
        "alarm or trip threshold calibration" in value
        for value in record["prohibited_inferences"]
    )
