# Safety Modeling Basis

## Standards and evidence

1. ISO 19880-3:2018 covers check, excess-flow, flow-control, manual, safety,
   shut-off, and breakaway valves for gaseous hydrogen stations through H70.
   <https://www.iso.org/standard/64754.html>
2. IEC 61511-1:2016 defines the lifecycle for specifying, designing, operating,
   and maintaining a process safety-instrumented system.
   <https://webstore.iec.ch/en/publication/24241>
3. ISO 4126-1:2013, confirmed in 2025, defines general product requirements for
   safety valves. The simulator does not claim certified sizing without the full
   applicable standard and vendor data.
   <https://www.iso.org/standard/50826.html>
4. HyRAM+ 6.1 fault-tree inputs include nozzle pop-off/failure to close, manual
   and solenoid valve failure to close, solenoid common cause, relief failure to
   open, breakaway failure to close, fueling overpressure, and drive-off.
   <https://pypi.org/project/hyram/>
5. The current HyRAM+ technical basis is SAND2025-04942.
   <https://doi.org/10.2172/2563814>

## Model separation

Continuous vessel, pipe, relief, and actuator physics remain in the ODE model.
Transmitters and trip logic execute at a fixed scan period. This prevents an
adaptive ODE solver from advancing mutable alarm timers more than once when it
re-evaluates a trial time point.

Transmitters use a first-order response:

```text
dPV/dt = (true_value + bias - PV) / tau_sensor
```

Trip rules support direction, delay, reset hysteresis, and latching. ESD
de-energizes configured actuators, so each valve's fail-safe position and closing
dynamics determine isolation time. A stuck fault holds actual valve position.

Pressure relief is a mass and enthalpy outlet to an ambient boundary. Effective
area increases from zero at absolute set pressure to full area at full-open
pressure; discharge uses the CoolProp real-gas nozzle model. Failure to open is
an independently injectable fault.

## Limits

- Example thresholds are not safety design recommendations.
- No SIL or PFD claim is made.
- Voting, diagnostic coverage, proof tests, bypasses, and common-cause beta
  factors require a reviewed project Safety Requirements Specification.
- HyRAM probabilities remain owned by the selected HyRAM version and are not
  copied into simulator defaults.
- Active release consequences still need automatic scheduling into HyRAM.
