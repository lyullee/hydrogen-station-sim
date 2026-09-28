"""Fault schedule and independent safety PLC configuration example."""

from h2station.safety_runtime import (
    FaultEvent,
    FaultInjector,
    FaultKind,
    FaultSchedule,
    SafetyLimits,
    SafetyPLC,
)


faults = FaultSchedule(
    (
        FaultEvent(
            event_id="hose-leak-01",
            kind=FaultKind.HYDROGEN_LEAK,
            target="dispenser.hose",
            start_time_s=45.0,
            leak_diameter_m=5.0e-4,
            indoor=False,
        ),
        FaultEvent(
            event_id="cooling-loss-01",
            kind=FaultKind.PRECOOLER_LOSS,
            target="dispenser.precooler",
            start_time_s=60.0,
            magnitude=0.0,
        ),
    )
)
fault_injector = FaultInjector(faults)
safety_plc = SafetyPLC(
    SafetyLimits(
        maximum_vehicle_pressure_pa=87.5e6,
        maximum_vehicle_temperature_k=358.15,
        maximum_precooler_outlet_temperature_k=253.15,
        maximum_flow_imbalance_kg_s=0.010,
        detector_alarm_volume_fraction=0.01,
        detector_trip_volume_fraction=0.02,
        trip_persistence_s=0.5,
    )
)

# Thresholds above are demonstrative, not an ISO 19880-1 compliance declaration.
# Site hazard analysis, detector certification, and licensed standards govern the
# production setpoints.

