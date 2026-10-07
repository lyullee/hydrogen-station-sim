from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _json(name: str) -> dict:
    return json.loads((ROOT / "research" / name).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def test_typeiii_protocol_and_source_are_frozen_before_outcome_access() -> None:
    protocol = _json("dickens_typeiii_prospective_protocol_2026_10_08.json")
    source = protocol["source"]
    assert protocol["status"] == "frozen_before_numerical_outcome_access"
    assert protocol["numerical_outcome_values_inspected_before_freeze"] is False
    assert protocol["frozen_model"]["parameter_fitting"] is False
    assert _sha256(ROOT / source["archive"]) == source["archive_sha256"]
    assert _sha256(ROOT / source["case_file"]) == source["case_file_sha256"]


def test_typeiii_negative_result_is_retained_without_raw_measurements() -> None:
    result = _json("dickens_typeiii_prospective_result_2026_10_08.json")
    assert result["source_hashes_match"] is True
    assert result["parameter_fitting"] is False
    assert result["post_outcome_parameter_change"] is False
    assert result["integrity_pass"] is True
    assert result["screen_results"] == {
        "pressure_nrmse_percent_measured_span": True,
        "pressure_rmse_mpa": True,
        "gas_temperature_rmse_k": False,
        "gas_temperature_peak_absolute_error_k": False,
    }
    assert result["joint_primary_screen_pass"] is False
    assert result["claim_supported"] is False
    serialized = json.dumps(result)
    assert "measured_pressure_pa" not in serialized
    assert "measured_temperature_k" not in serialized


def test_post_outcome_mixed_convection_cannot_promote_validation() -> None:
    diagnostic = _json(
        "dickens_typeiii_mixed_convection_diagnostic_2026_10_08.json"
    )
    assert diagnostic["post_outcome"] is True
    assert diagnostic["parameter_fitting"] is False
    assert diagnostic["runtime_parameter_updated"] is False
    assert diagnostic["frozen_validation_result_unchanged"] is True
    assert diagnostic["validation_gate_effect"] == "none"
    assert diagnostic["correlation"]["empirical_factor_two_used"] is False
    assert diagnostic["method_sources"]["source_code_copied"] is False
    assert diagnostic["method_sources"]["public_reference_license"] == "GPL-3.0"
    assert len(diagnostic["runs"]) == 3
    assert all(run["joint_primary_screen_pass"] for run in diagnostic["runs"])
