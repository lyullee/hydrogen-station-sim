# Runtime evidence, uncertainty, and paired response runs

## Runtime evidence gate

Every native or unavailable consequence result carries `runtime_evidence_gate`.
The gate records model identity/version, validation state, applicability range,
input quality, uncertainty state, evidence artifacts, permitted advisory use, and
all reasons automatic actuation is blocked. The present
`COMPONENT_ONLY_NO_FULL_LOOP` result is suitable for operator/LLM screening when
inputs are usable, but it cannot authorize a valve, vent, ESD, or restart command.
Independent deterministic PLC/interlock logic remains outside this model gate.

## Bounded consequence sensitivity

`h2station.risk.consequence_uncertainty.consequence_uncertainty_screen` samples
declared pressure, temperature, aperture, and discharge-coefficient bounds with a
fixed seed. It returns P05/P50/P95 for available mass-flow and consequence outputs,
plus an input-sensitivity ranking. The calculation is on demand and capped at 128
samples so it does not enter the high-frequency monitor loop.

These percentiles describe the declared sensitivity ensemble. They are not
confidence intervals, site safety distances, or validated evacuation radii.

## Automatic paired response experiment

`POST /api/simulations/counterfactual-batch` accepts one finite `SimulationInput`
and an intervention time. It launches four jobs with identical initial conditions,
fault inputs, solver step, and model settings:

- `no_action`
- `isolation`
- `esd`
- `esd_isolation_ventilation`

Scheduled commands are consumed by the same simulation-clock callback as live
operator commands. Each run retains command, position feedback, flow confirmation,
before/after metrics, and the existing training score. Results should be compared
only after all four jobs complete. They are virtual counterfactuals and do not prove
field emergency effectiveness.

## Additional fault coverage

- `partial_closed` leaves 25% of the virtual valve flow path and makes a full-close
  confirmation fail.
- `sensor-dropout` preserves the last numeric value but marks it `BAD` and identifies
  the simulated dropout origin.
- `sensor-clock-skew` delays the sensor timestamp, marks it `STALE`, and identifies
  the simulated clock-skew origin.
- after ESD and confirmed immediate stop, the injected source can end while
  `residual_hazard` remains `monitoring`. Three consecutive samples with negligible
  leak, less than 0.2 vol% H2, good detector quality, and no ventilation fault are
  required to clear it.

The combined regression deliberately includes partial closure, false valve
feedback, ventilation failure, ESD, source termination, and delayed residual-hazard
clearance.
