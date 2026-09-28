# Closed-loop safe operation

## Runtime order

`SafeFullStationSimulator` combines the full physical station, deterministic faults,
the independent safety PLC, dynamic leak source terms, and HyRAM consequences. Each
fixed control interval executes in causal order:

1. Reconstruct current CoolProp states and instrument readings
2. Apply sensor faults
3. Evaluate the safety PLC and latched ESD
4. Evaluate normal fueling and cascade controls
5. Apply physical actuator faults after safety commands
6. Calculate leak flow and update HyRAM consequences
7. Feed HyRAM detector concentration outputs into the next PLC scan
8. Integrate mass, energy, wall, hose, precooler, and vehicle states with BDF

Safety commands take priority over normal commands. A physical stuck-open fault takes
priority over the commanded safe position, allowing intended failure scenarios
to continue releasing hydrogen until another isolation boundary closes.

## Physical leak feedback

Leaks are no longer consequence-only calculations. At every ODE evaluation the leak
mass and associated flow enthalpy are removed from the selected source:

```text
dm_source/dt = other mass flows - mdot_leak
dU_source/dt = other energy flows - mdot_leak * h_source
```

Supported source IDs are:

- `cascade.<bank-name>`
- `dispenser.hose`
- `vehicle.tank`

The same real-gas mass flow is passed to HyRAM through
`mass_flow_override_kg_s`. This prevents the safety model and physical inventory
model from using inconsistent release rates.

## Detector feedback

HyRAM consequence backends may return either:

```text
detector_concentrations = {detector_id: hydrogen volume fraction}
```

or:

```text
maximum_concentration = hydrogen volume fraction
```

These values are applied at the following PLC sample, representing calculation,
communication, and scan latency. A site-specific extractor can replace the default
mapping when detector locations are evaluated from plume or enclosure fields.

## ESD continuation

The simulation does not terminate when ESD activates. It continues to the requested
end time so that the following quantities remain observable:

- Trip-to-isolation delay
- Cascade valve closing transient
- Residual hose discharge
- Continued release under stuck-open faults
- Total released mass
- Time evolution of concentration, thermal radiation, and overpressure consequences

This matches the purpose of an emergency shutdown: transition the process toward a
safe state rather than treating the trip itself as the end of the physical event.

## HyRAM interpretation

HyRAM+ provides release, flame, plume, accumulation, overpressure, harm, and QRA
models. The runtime stores instantaneous consequence outputs separately from annual
risk metrics. Annualized risk is only calculated when a traceable component failure
frequency, ignition probability, and HyRAM harm probability are all available.

Sandia HyRAM+ documentation:
https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/

ISO 19880-1 scope and safety-system context:
https://www.iso.org/standard/71940.html

## Remaining work

- Bind the existing `HyRAMAdapter`/`DynamicRiskCoordinator` outputs to
  `CallableHyRAMBackend` for each outdoor and indoor release type.
- Add explicit detector geometry and transport delay rather than a single-scan delay.
- Add independent upstream/downstream isolation valves and trapped-volume blowdown.
- Add proof-test, dangerous-undetected failure, and shutdown-failure probabilities.
- Execute nominal and fault validation cases only after parameter provenance files
  and acceptance limits have been approved.
