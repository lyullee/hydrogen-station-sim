"""Sampled ESD setup for the illustrative station model."""

from h2station import (
    DynamicSensor,
    FlowTripRule,
    SafetyActions,
    SafetyCoSimulator,
    SafetySupervisor,
    SensorParameters,
    SensorVariable,
    TripRule,
)

from basic_station import build_station, commands


station, initial = build_station()
supervisor = SafetySupervisor(
    sensors=(
        DynamicSensor(SensorParameters("PT_VEHICLE", "vehicle", SensorVariable.PRESSURE, 0.08, 0.0, 100.0e6)),
        DynamicSensor(SensorParameters("TT_VEHICLE", "vehicle", SensorVariable.TEMPERATURE, 0.25, 173.15, 423.15)),
    ),
    trip_rules=(
        TripRule("PSHH_VEHICLE", "PT_VEHICLE", 87.5e6, 82.5e6, delay=0.1),
        TripRule("TSHH_VEHICLE", "TT_VEHICLE", 358.15, 353.15, delay=0.2),
    ),
    flow_trip_rules=(
        FlowTripRule("FSHH_DISPENSER", "dispenser_hose.face_1", 0.060, delay=0.1),
    ),
    actions=SafetyActions(
        stop_compressors=("charge_low", "charge_mid", "charge_high"),
        deenergize_actuators=("dispense_low", "dispense_mid", "dispense_high"),
    ),
)
simulator = SafetyCoSimulator(station, supervisor, commands, 298.15, scan_period=0.1)

# Execute only after replacing illustrative thresholds with a reviewed SRS.
