from __future__ import annotations

import json
from pathlib import Path

import pytest

from h2station.release_network_development import series_effective_conductance_m2


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research" / "release_network_development.json"


def test_series_conductance_is_bounded_by_each_restriction():
    effective = series_effective_conductance_m2(
        nozzle_diameter_mm=3.0,
        nozzle_discharge_coefficient=0.91,
        supply_diameter_mm=2.62,
        supply_discharge_coefficient=0.8,
    )
    nozzle_only = 0.91 * 3.141592653589793 * (0.003**2) / 4.0
    supply_only = 0.8 * 3.141592653589793 * (0.00262**2) / 4.0
    assert effective < nozzle_only
    assert effective < supply_only


def test_diagnostic_cannot_be_presented_as_confirmatory_validation():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["evidence_role"] == "consumed_development_only"
    assert result["eligible_as_confirmatory_validation"] is False
    assert result["interpretation"]["claim_supported"] is False
    assert all(result["contamination_disclosure"].values())


def test_proust_selected_restriction_fails_to_transfer_across_imamura_diameters():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    model = result["models"]["proust_selected_series_restriction"]
    proust = model["proust"]
    imamura = model["imamura"]
    assert all(item["within_reference_screen"] for item in proust)
    assert [item["within_reference_screen"] for item in imamura] == [True, True, False, False]
    assert imamura[-1]["nrmse_percent_peak_measured"] == pytest.approx(41.81, abs=0.02)


def test_unrestricted_cd_one_is_better_for_consumed_imamura_series():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    series_model = result["models"]["proust_selected_series_restriction"]["imamura"]
    aperture_model = result["models"]["direct_aperture_cd_1_0"]["imamura"]
    assert all(item["within_reference_screen"] for item in aperture_model)
    assert sum(item["nrmse_percent_peak_measured"] for item in aperture_model) < sum(
        item["nrmse_percent_peak_measured"] for item in series_model
    )
