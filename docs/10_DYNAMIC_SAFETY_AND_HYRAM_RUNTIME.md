# Dynamic safety and HyRAM runtime contract

## Safety architecture

The dynamic safety layer is independent of the normal fueling controller. A sampled
`SafetyPLC` receives instrument readings, applies persistence timers, latches an ESD,
and requires an explicit manual reset after all trip conditions clear.

The modeled protective actions are:

- Isolate the hydrogen supply
- Close the PCV
- Close cascade discharge valves
- Stop the compressor
- Keep safety monitoring energized
- Preserve all initiating causes until manual reset

This follows the publicly visible ISO 19880-1 concepts of risk management, safety
functions, emergency shutdown, isolation, and continued safe monitoring. Exact
setpoints are not copied from the licensed standard and must be supplied by the site
safety requirements specification.

Official scope: https://www.iso.org/standard/71940.html

## Fault injection

`FaultSchedule` supports deterministic start/end times for:

- Sensor bias and frozen sensor values
- PCV stuck open or closed
- Cascade valve stuck open or closed
- Precooler capacity loss
- Compressor trip
- Hydrogen leaks with physical hole diameter
- Manual emergency stop

Fault injection is kept separate from component equations. This allows the same
physical model to be used for nominal validation and fault campaigns and prevents
calibration factors from silently representing failures.

## Dynamic leak source term

Leaks use the same CoolProp/SciPy real-gas restriction model as the dispenser. At
each safety sample, current component pressure and temperature generate a new mass
flow. Released mass is integrated in time:

```text
m_released(t + dt) = m_released(t) + mdot_leak(t) * dt
```

The leak flow must also be removed from the associated physical control volume when
the safety runtime is connected to the full-station ODE. This feedback connection is
the next implementation step.

## HyRAM+ interface

`HyRAMDynamicReleaseRequest` is the versioned runtime contract. It contains:

- Source pressure and temperature
- Ambient pressure
- Physical orifice diameter and discharge coefficient
- Simulator-calculated `mass_flow_override_kg_s`
- Explicit release-source boundary: `free_orifice` or `flow_limited_line`
- Optional defensible process/line flow cap for a flow-limited boundary
- Cumulative released mass and elapsed release duration
- Release location, angle, height, and indoor/outdoor flag
- Optional annual leak frequency and ignition probabilities

`DynamicRiskMonitor` updates the lightweight leak source term at every safety scan
but rate-limits the more expensive HyRAM consequence call. The default conceptual
flow is:

```text
station state -> leak source term -> HyRAM jet/plume/flame/overpressure/accumulation
              -> detector concentration -> SafetyPLC -> isolation -> station state
```

The local HyRAM+ adapter should implement `HyRAMConsequenceBackend.evaluate_release`
and pass `mass_flow_override_kg_s` to the existing consequence methods. HyRAM+ 6.1
is the target version. The process model applies a flow cap before creating the
request and preserves both the boundary label and cap in the consequence output.
The cap must come from a stated equipment or benchmark boundary; it is not fitted
after viewing a desired consequence distance. Because HyRAM 6.1 can recompute a
choked orifice flow, the native bridge converts an active cap to an analytically
area-scaled equivalent consequence orifice. Results retain both the physical
aperture and the equivalent diameter, together with an approximation flag.

Official HyRAM+ page and technical references:
https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/

## Consequence versus risk

The runtime deliberately separates:

- **Dynamic consequence:** current release rate, plume, heat flux, overpressure,
  concentration, and accumulated mass
- **Annualized risk:** component leak frequency multiplied by scenario and harm
  probabilities

Pressure changing during one fill changes the consequence. It does not by itself
change a component's annual failure frequency. An annualized value is returned only
when a traceable frequency and HyRAM harm probability are both supplied.

Recent uncertainty work confirms that leak frequencies, ignition probabilities,
shutdown failure, isolation probability, and occupant locations should be treated as
uncertain QRA inputs rather than deterministic process states:
https://doi.org/10.1016/j.ress.2024.110139

## Current integration boundary

The safety PLC, fault injector, and HyRAM runtime contract are implemented. The next
phase will connect `OperationalOverride` and active leak mass/energy sinks directly
to `FullStationModel`, feed HyRAM indoor concentration back to detector readings, and
record trip-to-isolation response time and total released mass.
