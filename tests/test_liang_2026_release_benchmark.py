from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from h2station.liang_2026_release_benchmark import (
    RUNTIME_DISCHARGE_COEFFICIENT,
    evaluate,
    load_points,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/public_validation/derived/liang_2026_table2.csv"
PROTOCOL = ROOT / "research/liang_2026_release_benchmark_protocol.json"
RESULT = ROOT / "research/liang_2026_release_benchmark_2026_10_13.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_liang_table2_transcription_is_complete_and_monotone():
    points = load_points(DATA)
    assert len(points) == 7
    assert points[0].nozzle_pressure_mpa == pytest.approx(11.124)
    assert points[-1].nozzle_pressure_mpa == pytest.approx(63.999)
    assert points[0].measured_mass_flow_kg_min == pytest.approx(0.19)
    assert points[-1].measured_mass_flow_kg_min == pytest.approx(0.98)
    assert [item.paper_real_cd for item in points] == [
        0.60, 0.60, 0.58, 0.58, 0.57, 0.57, 0.57
    ]


def test_liang_zero_fit_benchmark_separates_equation_and_coefficient_error():
    result = evaluate(DATA)
    runtime = result["runtime_model"]
    parity = result["real_gas_equation_parity"]
    diagnostic = result["diagnostic_only_cd_0_6"]

    assert RUNTIME_DISCHARGE_COEFFICIENT == 0.8
    assert runtime["joint_screen_pass"] is False
    assert runtime["metrics"]["median_absolute_percentage_error"] == pytest.approx(
        39.04693043295592
    )
    assert runtime["metrics"]["nrmse_percent_of_observed_peak"] == pytest.approx(
        28.426666827358154
    )
    assert runtime["metrics"]["mean_percentage_bias"] > 38.0
    assert parity["joint_screen_pass"] is True
    assert parity["metrics"]["median_absolute_percentage_error"] < 1.0
    assert diagnostic["metrics"]["median_absolute_percentage_error"] < 5.0
    assert diagnostic["not_promoted_to_runtime"] is True


def test_liang_protocol_and_result_preserve_postaccess_claim_boundary():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))

    assert protocol["outcomes_accessed_before_protocol"] is True
    assert protocol["parameter_fitting_allowed"] is False
    assert protocol["production_model_change_allowed"] is False
    assert result["outcomes_accessed_before_protocol"] is True
    assert result["parameter_fitting"] is False
    assert result["production_model_parameter_changed"] is False
    assert result["decision"]["runtime_action"] == (
        "UNCHANGED_PENDING_GEOMETRY_SPECIFIC_EXTERNAL_VALIDATION"
    )
    assert result["protocol_sha256"] == _sha256(PROTOCOL)
    assert result["data_sha256"] == _sha256(DATA)
    assert result["locked_input_hashes_verified"] is True
    for item in protocol["locked_inputs"]:
        assert item["sha256"] == _sha256(ROOT / item["path"])
