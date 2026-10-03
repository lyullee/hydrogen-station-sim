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
