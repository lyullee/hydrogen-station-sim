from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/qra_multimethod_comparison_protocol_2026_10_08.json"
RESULT = ROOT / "research/qra_multimethod_comparison_2026_10_08.json"


def load_script():
    path = ROOT / "scripts/audit_qra_multimethod_benchmark.py"
    spec = importlib.util.spec_from_file_location("qra_multimethod", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_protocol_preserves_postaccess_nonvalidation_boundary() -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    assert payload["source"]["dataset_doi"] == "10.34810/DATA3632"
    assert payload["source"]["dataset_version"] == "2.0"
    assert payload["access_attestation"]["limited_numerical_rows_inspected_before_freeze"] is True
    assert payload["frozen_selection"]["selected_file_count"] == 46
    assert payload["reporting_rule"]["pass_fail_allowed"] is False
    assert payload["reporting_rule"]["model_tuning_allowed"] is False
    assert payload["evidence_classification"]["experimental_validation"] is False
    assert payload["evidence_classification"]["actual_incident_validation"] is False
    assert payload["evidence_classification"]["goal_completion_permitted"] is False


def test_manifest_is_exactly_seven_methods_and_four_equipment_classes() -> None:
    module = load_script()
    files = module.QRA_FILES

    assert len(files) == 46
    assert len({item[0] for item in files}) == 46
    assert {item[1] for item in files} == {f"M{index}" for index in range(1, 8)}
    assert {item[3] for item in files} == {"Supply", "Compressor", "Buffer", "Dispenser"}
    assert {item[4] for item in files} == {"explosion", "jet_fire"}


def test_log_interpolation_is_bounded_and_does_not_extrapolate() -> None:
    module = load_script()

    value = module.log_interpolate_distance(4.0, 20.0, 12.5, 8.0, 5.0)
    assert value is not None
    assert 8.0 < value < 20.0
    assert module.log_interpolate_distance(4.0, None, 12.5, 8.0, 5.0) is None
    with pytest.raises(ValueError):
        module.log_interpolate_distance(4.0, 20.0, 12.5, 8.0, 20.0)


def test_committed_result_retains_every_file_and_no_validation_claim() -> None:
    payload = json.loads(RESULT.read_text(encoding="utf-8"))

    assert payload["status"] == "completed_postaccess_descriptive_multimethod_comparison"
    assert payload["selection"]["file_count"] == 46
    assert payload["selection"]["method_count"] == 7
    assert payload["aggregate"]["observation_count"] > 0
    assert payload["aggregate"]["matched_input_group_count"] > 0
    assert payload["integrity"]["all_selected_files_present"] is True
    assert payload["integrity"]["value_based_exclusions"] == 0
    assert payload["integrity"]["model_tuning_performed"] is False
    assert payload["integrity"]["experimental_validation"] is False
