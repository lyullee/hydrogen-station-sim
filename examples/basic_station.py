"""Illustrative H70 station topology; parameters are not a validated design."""

from __future__ import annotations

import numpy as np

from h2station import (
    CompressorConnection,
    CompressorParameters,
    FiniteUAPrecooler,
    FiniteVolumePipe,
    HydrogenEOS,
    LumpedTank,
    MultistageCompressor,
    NetworkCommands,
    PrecoolerParameters,
    PipeParameters,
    PressureReliefParameters,
    PressureReliefValve,
    RealGasRestriction,
    RestrictionConnection,
    RestrictionParameters,
    StationNetwork,
    TankParameters,
    ValveActuator,
    ValveActuatorParameters,
    VentConnection,
)


def tank(eos: HydrogenEOS, volume: float, area: float, wall_capacity: float) -> LumpedTank:
    return LumpedTank(
        TankParameters(
            volume=volume,
            gas_wall_area=area,
            wall_ambient_area=area,
            wall_heat_capacity=wall_capacity,
            gas_wall_htc=120.0,
            wall_ambient_htc=8.0,
        ),
        eos,
    )


def build_station() -> tuple[StationNetwork, dict]:
    eos = HydrogenEOS()
    tanks = {
        "source": tank(eos, 2.0, 14.0, 2.0e6),
        "cascade_low": tank(eos, 0.35, 4.0, 8.0e5),
        "cascade_mid": tank(eos, 0.35, 4.0, 8.0e5),
        "cascade_high": tank(eos, 0.35, 4.0, 8.0e5),
        "vehicle": tank(eos, 0.122, 2.2, 5.5e5),
        "dispenser": tank(eos, 0.0015, 0.25, 6.0e4),
    }
    initial = {
        "source": tanks["source"].initial_inventory(20.0e6, 298.15),
        "cascade_low": tanks["cascade_low"].initial_inventory(45.0e6, 298.15),
        "cascade_mid": tanks["cascade_mid"].initial_inventory(65.0e6, 298.15),
        "cascade_high": tanks["cascade_high"].initial_inventory(95.0e6, 298.15),
        "vehicle": tanks["vehicle"].initial_inventory(3.5e6, 298.15),
        "dispenser": tanks["dispenser"].initial_inventory(3.5e6, 233.15),
    }

    compressor_model = MultistageCompressor(
        CompressorParameters(
            stages=3,
            rated_mass_flow=0.035,
            reference_inlet_density=eos.state_pt(20.0e6, 298.15).density,
        ),
        eos,
    )
    compressor_connections = tuple(
        CompressorConnection(
            name=f"charge_{bank}",
            source="source",
            target=f"cascade_{bank}",
            compressor=compressor_model,
        )
        for bank in ("low", "mid", "high")
    )

    dispenser_restriction = RealGasRestriction(
        RestrictionParameters(
            diameter=0.0020,
            discharge_coefficient=0.82,
            characteristic="equal_percentage",
        ),
        eos,
    )
    precooler = FiniteUAPrecooler(
        PrecoolerParameters(nominal_ua=3_500.0, coolant_temperature=213.15),
        eos,
    )
    dispenser_actuator = ValveActuator(
        ValveActuatorParameters(
            opening_time_constant=0.35,
            closing_time_constant=0.12,
            maximum_opening_rate=2.0,
            maximum_closing_rate=5.0,
            fail_safe_position=0.0,
        )
    )
    restriction_connections = tuple(
        RestrictionConnection(
            name=f"dispense_{bank}",
            source=f"cascade_{bank}",
            target="dispenser",
            restriction=dispenser_restriction,
            precooler=precooler,
            actuator=dispenser_actuator,
        )
        for bank in ("low", "mid", "high")
    )
    hose = FiniteVolumePipe(
        PipeParameters(
            length=4.0,
            inner_diameter=0.0040,
            outer_diameter=0.0120,
            absolute_roughness=1.5e-6,
            segments=4,
            wall_density=1_300.0,
            wall_specific_heat=1_400.0,
            internal_htc=180.0,
            external_htc=10.0,
            minor_loss_coefficient=8.0,
        ),
        eos,
    ).build(
        name="dispenser_hose",
        source="dispenser",
        target="vehicle",
        initial_pressure=3.5e6,
        initial_temperature=298.15,
    )
    tanks.update(hose.tanks)
    initial.update(hose.initial_inventories)
    all_restrictions = restriction_connections + hose.connections
    vents = (
        VentConnection(
            name="cascade_high_prv",
            source="cascade_high",
            relief_valve=PressureReliefValve(
                PressureReliefParameters(
                    set_pressure=98.0e6,
                    full_open_pressure=103.0e6,
                    diameter=0.0030,
                ),
                eos,
            ),
        ),
    )
    return StationNetwork(tanks, all_restrictions, compressor_connections, vents), initial


def commands(time: float, states: dict) -> NetworkCommands:
    speeds: dict[str, float] = {}
    openings: dict[str, float] = {}

    recharge_targets = (
        ("high", 94.0e6),
        ("mid", 64.0e6),
        ("low", 44.0e6),
    )
    for bank, threshold in recharge_targets:
        if states[f"cascade_{bank}"].pressure < threshold:
            speeds[f"charge_{bank}"] = 1.0
            break

    if time >= 2_400.0 and states["vehicle"].pressure < 70.0e6:
        for bank in ("low", "mid", "high"):
            if states[f"cascade_{bank}"].pressure > states["vehicle"].pressure + 2.0e6:
                openings[f"dispense_{bank}"] = 0.35
                break

    return NetworkCommands(openings, speeds)


if __name__ == "__main__":
    station, initial_inventory = build_station()
    result = station.simulate(
        initial_inventory,
        time_span=(0.0, 2_700.0),
        command_provider=commands,
        ambient_temperature=298.15,
        evaluation_times=np.linspace(0.0, 2_700.0, 271),
        maximum_step=2.0,
    )
    print(result.solver_message)
