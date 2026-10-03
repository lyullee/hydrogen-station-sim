from __future__ import annotations

from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario


def _station_and_gases():
    built = build_reference_scenario(ReferenceScenario(), UnavailableHyRAMBackend())
    gases = tuple(
        bank.gas_state(state)
        for bank, state in zip(built.station.banks, built.initial_state.banks)
    )
    return built.station, gases


def test_dispatch_progresses_low_to_high_without_falling_back():
    station, gases = _station_and_gases()
    supervisor = station.supervisor

    assert supervisor.select_dispatch_bank(station.banks, gases, 5.0e6) == 0
    assert supervisor.select_dispatch_bank(station.banks, gases, 46.0e6) == 1
    assert supervisor.select_dispatch_bank(station.banks, gases, 5.0e6) == 1
    assert supervisor.select_dispatch_bank(station.banks, gases, 66.0e6) == 2
    assert supervisor.select_dispatch_bank(station.banks, gases, 5.0e6) == 2


def test_dispatch_latches_are_independent_and_resettable():
    station, gases = _station_and_gases()
    supervisor = station.supervisor

    assert supervisor.select_dispatch_bank(
        station.banks, gases, 46.0e6, circuit_id="primary"
    ) == 1
    assert supervisor.select_dispatch_bank(
        station.banks, gases, 5.0e6, circuit_id="secondary"
    ) == 0

    supervisor.reset_dispatch("primary")
    assert supervisor.select_dispatch_bank(
        station.banks, gases, 5.0e6, circuit_id="primary"
    ) == 0
    assert supervisor.select_dispatch_bank(
        station.banks, gases, 5.0e6, circuit_id="secondary"
    ) == 0
