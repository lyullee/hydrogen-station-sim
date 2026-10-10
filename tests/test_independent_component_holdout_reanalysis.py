from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_public_type_iv_holdout_reanalysis_matches_frozen_source() -> None:
    source_path = ROOT / "research/tank_model_validation_v2.json"
    source = _json("research/tank_model_validation_v2.json")
    record = _json("research/independent_component_holdout_reanalysis_2026_10_11.json")
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()

    assert record["status"] == "READY_WITH_FROZEN_PUBLIC_SPLIT"
    assert record["integrity"]["source_hash_sha256"] == source_hash
    assert record["integrity"]["new_parameter_fit"] is False
    assert record["eligible_cases"]["calibration"] == len(source["calibration_case_ids"])
    assert record["eligible_cases"]["validation"] == len(source["validation_case_ids"])
    assert record["eligible_cases"]["validation_holdout_case_ids"] == source["validation_case_ids"]
    assert record["validation_metrics"]["pressure_rmse_mpa_mean"] == source["validation"]["pressure_rmse_mpa"]["mean"]
    assert record["validation_metrics"]["temperature_rmse_c_mean"] == source["validation"]["temperature_rmse_c"]["mean"]
    assert "station controller" in record["claim_boundary"]
