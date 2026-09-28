# Cascade valve sequencing

## Purpose

Ideal, instantaneous bank switching can hide pressure interruptions and can also
produce nonphysical flow spikes if two storage banks are treated as connected at
the same instant. The full-station model now uses a sampled hybrid valve sequencer
between the cascade supervisor and the continuous thermodynamic model.

## State machine

The default transition is break-before-make:

```text
OPEN(old) -> CLOSING(old) -> DEAD-TIME -> OPENING(new) -> OPEN(new)
```

Only one cascade discharge bank can supply the PCV at a time. The effective PCV
opening is the fueling controller command multiplied by the active cascade-valve
opening. During closing and dead time, hose line-pack can continue feeding the
vehicle and its pressure response remains part of the simulation.

The sequencer is updated only at the fixed supervisory sample interval. It is never
updated at the adaptive BDF solver's internal evaluation points.

## Fitting and hardware inputs

`CascadeValveSequencerParameters` exposes:

| Parameter | Meaning |
|---|---|
| `opening_time_constant_s` | Effective opening actuator response |
| `closing_time_constant_s` | Effective closing actuator response |
| `break_before_make_s` | Fully closed interval before the next bank opens |
| `closed_threshold` | Opening fraction treated as seated/fully open tolerance |

These values should be fitted from valve-position feedback, command timestamps,
P2 pressure, and dispenser mass-flow measurements. Pressure traces alone may not
uniquely distinguish actuator lag from flow-coefficient error.

## Literature alignment

Cascade studies describe initial use of the lower-pressure reservoir followed by a
switch to a higher level when the pressure difference can no longer maintain the
specified vehicle pressure rise. Recharge begins with the high-pressure reservoir:
https://doi.org/10.1016/j.ijhydene.2022.06.100

The public MathWorks model reports flow spikes during cascade switching when gas
from a higher-pressure bank leaks toward the lower-pressure bank, and recommends
adjusting valve timing:
https://www.mathworks.com/help/hydro/ug/hydrogen-refueling-station.html

The NREL station system report describes a priority panel, automatic shutoff valve,
and modulated variable-area flow-control device used to maintain the fueling ramp:
https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/58564.pdf

## Safety position

Break-before-make is the conservative default for preventing bank cross-flow, but
it is not asserted to reproduce every commercial priority panel. The real PLC cause
and effect, check-valve cracking pressure, valve fail position, proof-of-closure
feedback, and certified Cv curves must replace example parameters for a site model.

## Remaining work

- Explicit check-valve control volumes and cracking-pressure hysteresis
- Fail-open, fail-closed, stuck, delayed, and internal-leakage fault modes
- Compressor minimum run/off time and start/stop ramp
- Event records forwarded to the safety and HyRAM risk coordinator
- Validation of pressure interruption and flow spike against high-rate P2 data

