from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/oedi_h2safe_spatial_holdout_protocol_2026_10_14.json"
MODEL = ROOT / "src/h2station/prospective_spatial_rank.py"
PARENT = ROOT / "research/prospective_spatial_rank_protocol_2026_10_13.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_oedi_protocol_is_preaccess_and_hash_locks_existing_candidate() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    source = protocol["source"]
    candidate = protocol["locked_candidate"]

    assert source["detailed_landing_page_opened"] is False
    assert source["file_inventory_opened"] is False
    assert source["numerical_time_series_opened"] is False
    assert source["sensor_or_source_coordinate_values_opened"] is False
    assert source["outcome_plot_or_metric_opened"] is False
    assert candidate["implementation_sha256"] == _sha256(MODEL)
    assert candidate["parent_protocol_sha256"] == _sha256(PARENT)
    assert candidate["candidate_id"] == "pooled_spatial_rank_v1"


def test_oedi_protocol_retains_all_or_nothing_independent_holdout_rule() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    eligibility = protocol["eligibility"]
    decision = protocol["decision_rule"]

    assert eligibility["required_test_gas"] == "hydrogen"
    assert eligibility["minimum_eligible_case_count"] == 18
    assert eligibility["minimum_usable_sensor_count_per_case"] == 8
    assert "overlap" in eligibility["overlap_rule"].lower()
    assert decision["all_screens_must_pass"] is True
    assert decision["parameter_tuning_after_access_permitted"] is False
    assert len(decision["screens"]) == 5
    assert protocol["runtime_policy"]["enabled"] is False
    assert protocol["runtime_policy"]["alarm_or_trip_setpoint_change_permitted"] is False
