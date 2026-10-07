from __future__ import annotations

from dataclasses import replace

import pytest

from h2station.api import ProcessSettings, _serialize_result
from h2station.hazop.runtime import HazopMonitor
from h2station.operations import ProcessRuntime
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


def test_header_state_is_exposed_in_samples_and_result_series():
    built = _built()
    samples = []
    trajectory = built.simulator.simulate(
        built.initial_state,
        0.4,
        0.2,
        pace_idle=False,
        sample_callback=samples.append,
    )

    first = samples[0]
    assert first.header_pressure_pa == pytest.approx(45.0e6)
    assert first.header_temperature_k == pytest.approx(298.15)
    assert first.header_mass_kg == pytest.approx(
        built.initial_state.common_header.hydrogen_mass_kg
    )
    assert first.header_inflow_kg_s is not None

    payload = _serialize_result(
        trajectory,
        built.station,
        UnavailableHyRAMBackend(),
    )
    length = len(payload["series"]["time_s"])
    for key in (
        "header_pressure_mpa",
        "header_temperature_c",
        "header_mass_kg",
        "header_inflow_g_s",
    ):
        assert len(payload["series"][key]) == length
    assert payload["series"]["header_pressure_mpa"][0] == pytest.approx(45.0)


def test_cross_bank_reverse_flow_reaches_the_bank_hazop_rule():
    fault = FaultEvent(
        "header-check-valve-failure",
        FaultKind.CHECK_VALVE_FAILURE,
        "header",
        0.0,
        end_time_s=4.0,
    )
    built = _built(ReferenceScenario(
        duration_s=3.2,
        control_period_s=0.2,
        initial_vehicle_2_pressure_pa=60.0e6,
        fault_events=(fault,),
    ))
    built.simulator.process_runtime = ProcessRuntime(ProcessSettings(
        vehicle_1=True,
        vehicle_2=True,
    ).model_dump())
    built.simulator.hazop_monitor = HazopMonitor()
    observed_flow = []
    active_rules = set()

    def collect(sample):
        observed_flow.append(sample.hazop["signals"]["FT-0701"]["value"])
        active_rules.update(row["rule_id"] for row in sample.hazop["active"])

    built.simulator.simulate(
        built.initial_state,
        3.2,
        0.2,
        pace_idle=False,
        sample_callback=collect,
    )

    assert min(observed_flow) < -1.0
    assert "HZ-050" in active_rules
