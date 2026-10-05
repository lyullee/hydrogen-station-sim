import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "nbsdc_liquid_hrs_intake_protocol_2026_10_05.json"


def test_nbsdc_liquid_hrs_protocol_is_prospective_and_complete():
    data = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["status"] == "prospective_intake_contract"
    assert data["outcomes_accessed_before_freeze"] is False
    assert data["source"]["data_id"] == "67d50e37195d260905af9869"
    assert data["source"]["share_range_observed"] == "完全共享"
    assert len(data["expected_files"]) == 7
    required = data["required_channels"]
    for group in ("time", "vehicle_or_receptacle", "mass", "station_boundary", "protocol", "safety", "quality"):
        assert required[group]
    limits = data["eligibility_rule"]["screening_limits"]
    assert limits["pressure_rmse_mpa"] == 5.0
    assert limits["temperature_rmse_c"] == 10.0
    assert limits["transferred_mass_relative_error"] == 0.10
    assert "no parameter fitting" in data["eligibility_rule"]["holdout_rule"]
    assert "not evidence" in data["claim_boundary"]
