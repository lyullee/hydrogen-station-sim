"""Operator bank-fill settings initialize both pressure and hydrogen inventory."""

from dataclasses import replace
import time

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from h2station.api import SimulationInput, app
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario


def test_default_initial_bank_pressures_are_preserved():
    built = build_reference_scenario(ReferenceScenario(), UnavailableHyRAMBackend())
    pressures = [
        bank.gas_state(state).pressure_pa / 1e6
        for bank, state in zip(built.station.banks, built.initial_state.banks)
    ]
    assert pressures == pytest.approx([45.0, 65.0, 90.0], rel=1e-4)


def test_independent_fill_percent_changes_only_selected_bank_inventory():
    baseline = build_reference_scenario(ReferenceScenario(), UnavailableHyRAMBackend())
    changed = build_reference_scenario(
        replace(ReferenceScenario(), initial_bank_fill_percent=(50.0, 80.0, 100.0)),
        UnavailableHyRAMBackend(),
    )
    pressures = [
        bank.gas_state(state).pressure_pa / 1e6
        for bank, state in zip(changed.station.banks, changed.initial_state.banks)
    ]
    assert pressures == pytest.approx([25.0, 56.0, 100.0], rel=1e-4)
    assert changed.initial_state.banks[0].hydrogen_mass_kg < baseline.initial_state.banks[0].hydrogen_mass_kg
    assert changed.initial_state.banks[1].hydrogen_mass_kg < baseline.initial_state.banks[1].hydrogen_mass_kg
    assert changed.initial_state.banks[2].hydrogen_mass_kg > baseline.initial_state.banks[2].hydrogen_mass_kg


@pytest.mark.parametrize("field,value", [
    ("initial_bank_low_fill_percent", 0),
    ("initial_bank_medium_fill_percent", 101),
    ("initial_bank_high_fill_percent", -1),
])
def test_api_rejects_out_of_range_bank_fill(field, value):
    with pytest.raises(ValidationError):
        SimulationInput.model_validate({field: value})


def test_api_applies_bank_fill_settings_to_new_run():
    with TestClient(app) as client:
        response = client.post("/api/simulations", json={
            "duration_s": 0.2,
            "control_period_s": 0.2,
            "initial_bank_low_fill_percent": 50,
            "initial_bank_medium_fill_percent": 80,
            "initial_bank_high_fill_percent": 95,
        })
        assert response.status_code == 202
        job_id = response.json()["id"]
        for _ in range(200):
            job = client.get(f"/api/simulations/{job_id}").json()
            if job["status"] in {"complete", "failed"}:
                break
            time.sleep(0.02)
        assert job["status"] == "complete", job
        pressures = client.get(f"/api/simulations/{job_id}/result").json()["series"]["bank_pressure_mpa"]
        assert [pressures[name][0] for name in ("low", "medium", "high")] == pytest.approx(
            [25.0, 56.0, 95.0], rel=1e-3
        )
