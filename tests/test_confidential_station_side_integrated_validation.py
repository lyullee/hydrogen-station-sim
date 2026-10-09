from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/confidential_station_side_integrated_validation_2026_10_09.json"


def test_station_side_integrated_validation_combines_only_passed_holdouts() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    decision = result["decision"]
    assert result["artifact_type"] == "confidential_station_side_integrated_validation"
    assert decision["station_side_integrated_validation_supported"] is True
    assert decision["pressure_boundary_holdout_supported"] is True
    assert decision["cascade_sequence_holdout_supported"] is True
    assert decision["recharge_pressure_forecast_supported"] is True
    assert decision["lifecycle_counter_alignment_supported"] is False
    assert decision["runtime_parameter_application"] is False
    assert decision["vehicle_fill_validation"] is False
    assert decision["full_loop_external_validation_supported"] is False
    assert result["checks"]["cascade_sequence"]["holdout_pairs"] == 3664
    assert result["checks"]["recharge_pressure_forecast"]["holdout_cases"] == 394


def test_station_side_integrated_validation_is_reproducibly_hash_locked() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    for item in result["inputs"]:
        artifact = ROOT / item["artifact"]
        assert artifact.is_file()
        assert item["sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert all(value is False for value in result["privacy"].values())
    serialized = json.dumps(result, ensure_ascii=False)
    assert "C:\\" not in serialized
    assert '"raw_rows":' not in serialized
    assert "site_company_location" in serialized
