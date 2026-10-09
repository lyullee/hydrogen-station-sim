# Partial-station validation boundary

`scripts/run_partial_station_validation.py` evaluates the PCV, precooler, hose,
and vehicle-tank path against the public Powertech Labs J2601 Tables Method
traces already stored under `data/public_validation/processed/`.  It does not
claim that the compressor, cascade dispatch, or station inventory has been
validated, because those traces do not contain a measured upstream pressure
and temperature boundary.

The runner uses the measured inlet-gas-temperature trace as a time-dependent
delivery-temperature profile.  It uses a constant 90 MPa upstream pressure as
an explicit engineering assumption.  The pressure assumption is not a
measurement and the resulting report is marked
`development_diagnostic_only`.  It must not be used as an independent
holdout, a certification result, or a full-station IJHE performance claim.

The profile support is implemented in `ReferenceScenario` and
`FuelingSchedule`; empty profiles preserve the prior constant-boundary
behavior.  A frozen protocol should be created before any future confirmatory
run that has a genuinely new trace and an independently measured upstream
boundary.  The runner records whether its outcomes were already inspected,
the source commit, worktree state, boundary assumptions, controller
temperature-stop setting, case metrics, coverage, and stop reason.

## Reproduce the diagnostic

```powershell
$env:PYTHONPATH = "src"
& .\.venv\Scripts\python.exe scripts/run_partial_station_validation.py `
  --case-ids H2P-L01 H2P-L04 H2P-L11 H2P-L13 H2P-L19 H2P-L22 H2P-L29 H2P-L31
```

The default run keeps the model's 85 °C gas-temperature stop.  A high
temperature limit can be used only as a sensitivity analysis to distinguish
controller termination from the underlying flow/thermal mismatch:

```powershell
& .\.venv\Scripts\python.exe scripts/run_partial_station_validation.py `
  --case-ids H2P-L01 H2P-L04 H2P-L11 H2P-L13 H2P-L19 H2P-L22 H2P-L29 H2P-L31 `
  --maximum-gas-temperature-c 200 `
  --output data/public_validation/results/partial_station_profile_physics_only
```

Neither diagnostic run is a release gate.  The current development results
are retained with zero joint screen passes and show that the next model work
is the temperature/flow protocol state and upstream boundary, rather than
post-hoc parameter fitting to the consumed cases.

The already-consumed MC Default traces can be used only as a source-boundary
sensitivity diagnostic.  They contain a `source_pressure_1_mpa` channel, so
the following command exercises the same partial model with that published
profile.  It is not a new external holdout and does not change the frozen
0/8 full-loop result:

```powershell
& .\.venv\Scripts\python.exe scripts/run_partial_station_validation.py `
  --dataset mc_default --use-source-pressure-profile `
  --output data/public_validation/results/partial_station_mc_source_diagnostic
```

The MC workbook also contains a publisher pressure-reference schedule.  The
runner can apply it to the controller together with the measured source-3
pressure profile.  This is still a consumed, development-only sensitivity:

```powershell
& .\.venv\Scripts\python.exe scripts/run_partial_station_validation.py `
  --dataset mc_default --use-source-pressure-profile `
  --source-pressure-column source_pressure_3_mpa `
  --use-protocol-pressure-profile `
  --output data/public_validation/results/partial_station_mc_protocol_source3_physics_only
```

The pressure schedule is now a first-class optional controller boundary.  An
empty schedule preserves the constant APRR implementation, while a supplied
schedule is linearly interpolated on the controller clock and clamped at its
published endpoints.

## What the published MC boundary can and cannot establish

The published MC Default traces are useful even though they do not provide a
new independent station holdout.  The source-pressure trace and the published
pressure-reference schedule can be applied to the partial station boundary,
which separates two failure modes that otherwise look the same: an early
safety-temperature stop and a model that runs for the full fill but misses the
thermal, pressure, or SOC trajectory.  The reproducible aggregate comparison is
recorded in
[`research/partial_station_mc_boundary_diagnostic_2026_10_09.json`](../research/partial_station_mc_boundary_diagnostic_2026_10_09.json).

The safety-aware run uses the production 85 °C gas-temperature stop.  It
covers only part of the observed duration for several cases and has no joint
screening pass.  A separate 120 °C run is a diagnostic counterfactual only: it
covers the full observed duration, but its aggregate pressure, temperature, and
SOC errors are larger and it also has no joint pass.  The 120 °C value must not
be used as an operating limit or as a production retuning.  Neither run changes
the frozen external 0/8 result.

This is the useful engineering conclusion from the available public data: the
next high-value measurements are synchronised dispenser-inlet pressure,
delivered-gas temperature, mass flow, precooler/control state, and vehicle tank
pressure/temperature/SOC with declared units and stop-event semantics.  The
current model can already replay the station-side boundary and expose the
remaining mismatch without claiming that the whole station or field safety has
been validated.
