import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from recheck_confidential_equipment_drift import build_record  # noqa: E402


def test_drift_recheck_is_explicitly_non_promoting():
    fresh = {
        "files_read": 1,
        "sampled_rows": 4,
        "duration_s": 3.0,
        "median_sample_period_s": 1.0,
        "maximum_gap_s": 1.0,
        "boundary_pressure_pa": {
            "min": 50.0,
            "median": 51.0,
            "max": 52.0,
            "noise_sigma": 0.1,
            "positive_ramp_p95": 3.0,
        },
        "recharge_restart_margin_pa": 100.0,
        "state_transition_count": 2,
    }
    comparison = {"matches": False, "fields_compared": ["duration_s"], "mismatches": [{"field": "duration_s"}]}
    record = build_record(fresh, comparison)
    encoded = json.dumps(record, ensure_ascii=False)
    assert record["runtime_decision"]["profile_replaced"] is False
    assert record["runtime_decision"]["default_model_parameters_changed"] is False
    assert record["runtime_decision"]["mismatch_requires_custodian_review"] is True
    assert record["eligibility"]["full_loop_holdout_eligible"] is False
    assert '"source_paths_published": false' in encoded
    assert "tag_names" not in encoded


def test_committed_drift_artifact_is_privacy_bounded():
    path = ROOT / "research/confidential_station_equipment_drift_recheck_2026_10_06.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "confidential_station_equipment_drift_recheck"
    assert record["source_identifiers_published"] is False
    assert record["raw_rows_persisted"] is False
    assert record["runtime_decision"]["profile_replaced"] is False
    assert record["eligibility"]["full_loop_holdout_eligible"] is False
