import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_controlled_full_loop_cohort as cohort_prepare  # noqa: E402
from build_controlled_full_loop_registry import build_registry  # noqa: E402
from audit_ijhe_readiness import _controlled_registry_integrity  # noqa: E402


CRITERIA = {
    "pressure_rmse_mpa_max": 3.0,
    "temperature_rmse_c_max": 8.0,
    "mass_flow_rmse_g_s_max": 5.0,
    "selected_source_pressure_rmse_mpa_max": 3.0,
    "delivered_temperature_rmse_c_max": 8.0,
    "cascade_bank_pressure_rmse_mpa_max": 3.0,
    "dispatch_accuracy_min": 0.9,
    "compressor_state_accuracy_min": 0.9,
}
METRIC_NAMES = (
    "vehicle_pressure_mpa",
    "vehicle_temperature_c",
    "mass_flow_g_s",
    "delivered_temperature_c",
    "selected_source_pressure_mpa",
    "cascade_low_pressure_mpa",
    "cascade_medium_pressure_mpa",
    "cascade_high_pressure_mpa",
)


def _trace_hash(index: int) -> str:
    return f"{index:064x}"


def _receipt(index: int) -> dict:
    return {
        "trace_sha256": _trace_hash(index),
        "station_to_vehicle_trace_ready": True,
        "cascade_dispatch_evaluable": True,
        "full_loop_trace_ready": True,
        "evaluation_scope": "cascade_resolved_station_to_vehicle",
    }


def _result(index: int, passed: bool) -> dict:
    decisions = {name: passed for name in CRITERIA}
    return {
        "schema_version": 1,
        "artifact_type": "controlled_hrs_frozen_evaluation_result",
        "decision": "FROZEN_EVALUATION_PASS" if passed else "FROZEN_EVALUATION_FAIL",
        "evaluation_scope": "cascade_resolved_station_to_vehicle",
        "trace_sha256": _trace_hash(index),
        "source_commit": "locked-model-commit",
        "source_worktree_clean": True,
        "raw_rows_persisted": False,
        "source_identifiers_published": False,
        "absolute_timestamps_published": False,
        "acceptance_criteria": CRITERIA,
        "acceptance_by_metric": decisions,
        "metrics": {
            name: {
                "sample_count": 20,
                "rmse": float(index) / 10,
                "mae": float(index) / 20,
                "final_error": -float(index) / 30,
                "maximum_absolute_error": float(index) / 5,
            }
            for name in METRIC_NAMES
        },
        "state_metrics": {
            "selected_bank": {"sample_count": 20, "accuracy": 0.95},
            "compressor_active": {"sample_count": 20, "accuracy": 0.90},
        },
    }


def _write_cohort(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(cohort_prepare, "_git_commit", lambda: "locked-model-commit")
    receipts = []
    for index in range(1, 9):
        path = tmp_path / f"receipt-{index}.json"
        path.write_text(json.dumps(_receipt(index)), encoding="utf-8")
        receipts.append(path)
    protocol = cohort_prepare.prepare(receipts)
    protocol["frozen_before_case_outcomes"] = True
    protocol["individual_acceptance_criteria"] = CRITERIA
    protocol["evidence_design"] = {
        "independent_holdout": True,
        "model_developers_blinded_to_case_outcomes_before_freeze": True,
        "rights_cleared_for_controlled_evaluation": True,
    }
    path = tmp_path / "frozen-cohort.json"
    path.write_text(json.dumps(protocol), encoding="utf-8")
    return path


def _write_results(tmp_path: Path, pass_count: int = 7) -> list[Path]:
    paths = []
    for index in range(1, 9):
        path = tmp_path / f"result-{index}.json"
        path.write_text(json.dumps(_result(index, index <= pass_count)), encoding="utf-8")
        paths.append(path)
    return paths


def test_prepares_complete_preoutcome_case_set(tmp_path, monkeypatch):
    monkeypatch.setattr(cohort_prepare, "_git_commit", lambda: "locked-model-commit")
    receipt_paths = []
    for index in range(1, 9):
        path = tmp_path / f"receipt-{index}.json"
        path.write_text(json.dumps(_receipt(index)), encoding="utf-8")
        receipt_paths.append(path)

    protocol = cohort_prepare.prepare(receipt_paths)

    assert protocol["frozen_before_case_outcomes"] is False
    assert len(protocol["expected_trace_sha256"]) == 8
    assert protocol["cohort_acceptance"]["minimum_case_pass_fraction"] == 0.8
    assert protocol["evidence_design"]["independent_holdout"] is None


def test_registry_keeps_failures_and_hides_private_digests(tmp_path, monkeypatch):
    protocol = _write_cohort(tmp_path, monkeypatch)
    results = _write_results(tmp_path, pass_count=7)
    salt = tmp_path / "salt.bin"
    salt.write_bytes(b"private-test-salt-material-32-bytes-minimum")

    registry = build_registry(protocol, results, salt)

    assert registry["case_count"] == 8
    assert registry["case_pass_count"] == 7
    assert registry["case_pass_fraction"] == 0.875
    assert registry["full_loop_external_validation_supported"] is True
    assert sum(case["decision"] == "FROZEN_EVALUATION_FAIL" for case in registry["cases"]) == 1
    serialized = json.dumps(registry)
    assert all(_trace_hash(index) not in serialized for index in range(1, 9))
    assert "private-test-salt" not in serialized
    assert registry["privacy"]["raw_trace_hashes_published"] is False
    integrity, observed = _controlled_registry_integrity(registry)
    assert integrity is True
    assert observed["case_count"] == 8


def test_registry_rejects_selective_case_omission(tmp_path, monkeypatch):
    protocol = _write_cohort(tmp_path, monkeypatch)
    results = _write_results(tmp_path)[:-1]
    salt = tmp_path / "salt.bin"
    salt.write_bytes(b"private-test-salt-material-32-bytes-minimum")

    with pytest.raises(ValueError, match="one and only one result"):
        build_registry(protocol, results, salt)


def test_registry_does_not_promote_unattested_independence(tmp_path, monkeypatch):
    protocol_path = _write_cohort(tmp_path, monkeypatch)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["evidence_design"]["independent_holdout"] = False
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    results = _write_results(tmp_path)
    salt = tmp_path / "salt.bin"
    salt.write_bytes(b"private-test-salt-material-32-bytes-minimum")

    registry = build_registry(protocol_path, results, salt)

    assert registry["cohort_acceptance"]["numerical_screen_passed"] is True
    assert registry["provenance_screen_passed"] is False
    assert registry["full_loop_external_validation_supported"] is False


def test_registry_rejects_weakened_publication_case_floor(tmp_path, monkeypatch):
    protocol_path = _write_cohort(tmp_path, monkeypatch)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["cohort_acceptance"]["minimum_case_count"] = 7
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    salt = tmp_path / "salt.bin"
    salt.write_bytes(b"private-test-salt-material-32-bytes-minimum")

    with pytest.raises(ValueError, match="at least 8"):
        build_registry(protocol_path, _write_results(tmp_path), salt)


def test_readiness_gate_rejects_registry_that_exposes_trace_hashes(tmp_path, monkeypatch):
    protocol = _write_cohort(tmp_path, monkeypatch)
    salt = tmp_path / "salt.bin"
    salt.write_bytes(b"private-test-salt-material-32-bytes-minimum")
    registry = build_registry(protocol, _write_results(tmp_path), salt)
    registry["privacy"]["raw_trace_hashes_published"] = True

    integrity, observed = _controlled_registry_integrity(registry)

    assert integrity is False
    assert observed["raw_trace_hashes_published"] is True
