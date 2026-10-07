from __future__ import annotations

from dataclasses import replace

import pytest

from h2station.hazop.runtime import HazopMonitor
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario
from h2station.safety_runtime import FaultEvent, FaultKind


def _built(config: ReferenceScenario | None = None):
    return build_reference_scenario(
        config or ReferenceScenario(duration_s=0.4, control_period_s=0.2),
        UnavailableHyRAMBackend(),
    )


def test_common_header_round_trips_as_an_independent_inventory():
    built = _built()
    restored = type(built.initial_state).from_vector(
        built.initial_state.as_vector(), len(built.station.banks)
    )

    assert restored.common_header == built.initial_state.common_header
    assert restored.secondary_partial_station == built.initial_state.secondary_partial_station
    assert built.station.header_gas_state(restored).pressure_pa == pytest.approx(45.0e6)


def test_bank_header_path_is_one_way_until_check_valve_failure():
    built = _built()
    header_at_80_mpa = built.station.common_header.initial_state(80.0e6, 298.15)
    state = replace(built.initial_state, common_header=header_at_80_mpa)

    blocked = built.station.header_bank_mass_flows(
        state, (0, None), (1.0, 0.0)
    )
    reverse = built.station.header_bank_mass_flows(
        state, (0, None), (1.0, 0.0), allow_reverse_flow=True
    )

    assert blocked[0] == 0.0
    assert reverse[0] < 0.0
    assert reverse[1:] == (0.0, 0.0)


def test_header_leak_depletes_header_without_removing_high_bank_inventory():
    fault = FaultEvent(
        "header-leak",
        FaultKind.HYDROGEN_LEAK,
        "header",
        0.0,
        end_time_s=0.4,
        leak_diameter_m=1.0e-3,
    )
    built = _built(
        ReferenceScenario(
            duration_s=0.4,
            control_period_s=0.2,
            fault_events=(fault,),
        )
    )
    baseline = _built(
        ReferenceScenario(duration_s=0.4, control_period_s=0.2)
    )

    result = built.simulator.simulate(
        built.initial_state, 0.4, 0.2, pace_idle=False
    )
    reference = baseline.simulator.simulate(
        baseline.initial_state, 0.4, 0.2, pace_idle=False
    )

    assert (
        result.final_state.common_header.hydrogen_mass_kg
        < reference.final_state.common_header.hydrogen_mass_kg
    )
    assert result.final_state.banks[2].hydrogen_mass_kg == pytest.approx(
        reference.final_state.banks[2].hydrogen_mass_kg,
        rel=2.0e-5,
    )


def test_hazop_uses_header_state_inflow_and_inventory_for_mass_balance():
    built = _built()
    monitor = HazopMonitor()
    built.simulator.hazop_monitor = monitor

    built.simulator.simulate(
        built.initial_state, 0.2, 0.2, pace_idle=False
    )
    signals = monitor.latest["signals"]

    assert signals["PT-1001"]["origin"] == "PROCESS_STATE"
    assert signals["FT-1001"]["origin"] == "PROCESS_FLOW"
    assert signals["MASS_HEADER"]["origin"] == "PROCESS_INVENTORY"
    assert signals["MASS_HEADER"]["value"] == pytest.approx(
        built.initial_state.common_header.hydrogen_mass_kg
    )
