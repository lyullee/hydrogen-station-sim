# Development Progress

## 2026-10-08 - Confidential pressure/flow consistency boundary

- Added a streaming, privacy-bounded CSV audit for owner-controlled station
  pressure and flow-like channels.
- The result publishes no source path, filename, tag, exact timestamp or raw
  measurement row and cannot apply an unattested unit to the process model.
- Replaced the one-row derivative with predeclared 1, 10, 30 and 60 second
  mass-balance windows so quantized totalizers are evaluated at their effective
  update scale.
- Screened 3,053,442 rows from 20 pressure-and-flow tables. Twenty-seven of 54
  cumulative/instantaneous comparisons in 17 files met the joint consistency
  screen. Passing comparisons had median correlation 0.9971, median
  span-normalized RMSE 2.54%, and median derivative-to-signal scale 0.016648.
- Classified this as strong internal evidence for candidate flow/totalizer
  pairs, while keeping absolute mass-flow and conditional storage-volume
  fitting disabled until a custodian confirms the generic channel roles,
  units, sign/reset convention and calibration status.
- The complete regression suite passed after this update: 1,034 tests with no
  failures.
- Re-ran the built-in LaTeX compiler for the exact current IJHE draft. The host
  still reports `Unable to find standard directories for platform`, so the
  compilation gate remains pending rather than being inferred from the older
  PDF.

## 2026-09-07 - Modeling foundation

Status: implemented as the first code baseline; not yet validated against an
experimental filling trace.

Completed:

- Kept the legacy HTML outside the new model architecture.
- Selected a conventional gaseous H70 station reference topology.
- Added a CoolProp real-gas property provider.
- Added first-principles mass and energy balances for gas vessels and walls.
- Added real-gas isentropic restriction flow solved with SciPy optimization.
- Added multistage compressor and finite-UA precooler models.
- Added a reusable dynamic equipment network and stiff ODE integration path.
- Added a HyRAM+ 6.1 consequence adapter and evaluation scheduler.
- Recorded literature, open data, assumptions, and fitting variables.

Decisions:

- Use absolute pressure everywhere inside the model.
- Use SI units at every internal interface.
- Keep calibrated multipliers explicit and separate from geometric/design data.
- Use HyRAM for release consequences and QRA, not as the station process solver.
- Evaluate dynamic consequences on sampled process states; do not mislabel a
  consequence snapshot as a full time-varying QRA.
- Keep API and frontend work after the physical model interfaces stabilize.

Next modeling work:

- Add distributed or finite-volume piping with Darcy-Weisbach losses, line-pack,
  pipe-wall thermal inertia, fittings, and valve actuator dynamics.
- Add literature-traceable reciprocating/diaphragm compressor maps and thermal
  masses, including bypass and recycle behavior.
- Add cascade recharge/dispatch state machines and SAE J2601-compatible fueling
  protocol boundaries without copying proprietary tables into the repository.
- Add tank model levels: one-zone, gas/liner/shell three-zone, and optional axial
  multi-zone for high-aspect-ratio heavy-duty tanks.
- Define validation cases from H2FillS publications and public experimental data.
- Add uncertainty and parameter-estimation workflows only after identifiability
  and measurement mappings are documented.

## 2026-09-12 - Dynamic piping, hose, and valve actuation

Completed:

- Added a finite-volume pipe/hose factory with configurable spatial segments.
- Reused the vessel mass/energy/wall balance for line-pack and pipe-wall thermal
  inertia instead of introducing a second conservation implementation.
- Added compressible isothermal segment flow from `fluids`, iterated with the
  Darcy friction factor and CoolProp density/viscosity.
- Added a CoolProp real-gas isentropic nozzle cap for physically bounded flow and
  choking behavior during large startup pressure differences.
- Added distributed and minor pressure-loss parameters with explicit fitting
  multipliers for roughness, friction, heat transfer, and flow.
- Added first-order valve actuator states, asymmetric opening/closing rates,
  deadband, and fail-safe position to the network ODE.
- Updated the example to include a dispenser control volume and a four-cell hose.

Still required before validation:

- Select geometry and material properties from an actual station P&ID, line list,
  and hose datasheet; example values are illustrative only.
- Compare segment convergence and pressure-loss predictions against published or
  commissioning traces.
- Add momentum-state/wave dynamics only where water-hammer-scale transients are
  relevant; the present face flow is quasi-steady.
- Add check valve cracking pressure, excess-flow trip, breakaway isolation, and
  ESD logic as distinct components.

## 2026-09-12 - Safety devices and sampled ESD layer

- Added check-valve cracking behavior and proportional pressure-relief flow.
- Added ambient vent boundaries and a high-bank PRV example.
- Added dynamic pressure/temperature sensors and injectable sensor faults.
- Added delayed, hysteretic, latching pressure, temperature, and flow trips.
- Added compressor shutdown, valve de-energization, stuck actuator, relief
  failure, external trip, and operator E-stop behavior.
- Added a fixed-scan co-simulator so trip timers are not mutated inside adaptive
  ODE function evaluations.
- Matched simulator fault identifiers to HyRAM+ 6.1 dispenser failure modes.

Remaining safety work includes rupture disks, breakaway separation, vent-stack
piping, enclosure accumulation/detection, voting, proof testing, and validation
against a project cause-and-effect chart and Safety Requirements Specification.

## 2026-09-13 - Feature-complete prototype and verification

Completed:

- Added a gas/liner/CFRP three-zone Type IV vehicle tank and an external
  SAE J2601-compatible schedule boundary with APRR control and SOC termination.
- Added the dispenser train, three-bank cascade supervisor, compressor recharge,
  and break-before-make valve sequencing.
- Closed the loop between process dynamics, sampled sensors, faults, latched ESD,
  physical leak mass/enthalpy removal, and dynamic risk updates.
- Added a native HyRAM+ 6.1 runtime backend and retained the configurable external
  backend interface for deployment-specific integrations.
- Added canonical scenario definitions, H2FillS-compatible validation channels,
  a command-line server, asynchronous FastAPI jobs, and the responsive monitoring
  frontend.
- Added automated physics, conservation, safety, API, frontend, and integration
  tests plus reproducible development dependencies.

Verification evidence:

- Dependency consistency: `pip check` passed.
- Python syntax/import compilation: `compileall` passed.
- Final automated suite: 7 tests passed, including API lifecycle and native
  HyRAM consequence integration.
- Native HyRAM+ 6.1 smoke calculation returned heat flux, overpressure, impulse,
  visible flame length, and radiant fraction.
- API end-to-end check returned HTTP 200 for the UI assets and health endpoint,
  created an asynchronous simulation, reached 100 percent with `complete` status,
  and returned `series`, `events`, `risk_updates`, and `summary`.
- Browser check showed `전체 시스템 준비`, `HyRAM 연결됨`, and
  `HYRAM+ 6.1 NATIVE`; a one-second run updated pressure, temperature, SOC,
  cascade/compressor state, risk monitoring, timeline, and event history.

Compatibility decision:

- HyRAM+ 6.1 uses the legacy SciPy ODE callback contract. SciPy is constrained to
  `>=1.11,<1.16`; SciPy 1.18.1 fails inside HyRAM's jet model before consequence
  results are produced.
- For choked releases HyRAM may warn that its internal jet source recalculates
  choked flow instead of enforcing the supplied dynamic mass-flow override. The
  process solver's released mass remains authoritative for inventory accounting;
  this interface limitation must be included in benchmark and uncertainty work.

Status: 100 percent of the explicitly defined software prototype scope is
implemented. Experimental calibration, independent validation, licensed protocol
tables, site-specific engineering, and certification remain intentionally outside
that definition and are listed in the completion-status document.

## 2026-09-13 - Observable long-run progress

- Replaced the fixed 20-percent solve indicator with progress callbacks from the
  sampled closed-loop integration loop.
- Added current simulated time and requested duration to the asynchronous job
  status without changing the solver tolerance or control period.
- Updated the monitoring UI to display both percentage and simulated seconds, so
  a computationally expensive long run can be distinguished from a stalled job.

## 2026-09-13 - Solver telemetry and interactive speed modes

- Added a calculation-monitor dialog with phase, simulated time, completed
  integration intervals, wall time, estimated remaining time, backend identity,
  heartbeat age, and a compact activity log.
- Added explicit fast, balanced, and precision sampling modes to the UI. They use
  the same first-principles equations and adaptive BDF solver while trading sampled
  controller/safety time resolution for fewer integration restarts.
- The API now reports structured initialization, integration, serialization,
  completion, and failure states with timestamps instead of a fixed 20-percent
  indicator throughout the solve.

## 2026-09-13 - Live calculation streaming

- Refactored the closed-loop solver to emit a typed live sample after every
  completed control interval while retaining the final trajectory result.
- Added a FastAPI WebSocket stream for status and process frames, with the prior
  polling API retained as an automatic browser fallback.
- Updated the primary dashboard during calculation with vehicle, hose, cascade,
  flow, ESD, risk, timeline, and trend data instead of waiting for completion.
- Retained the completed-run timeline for replay and added versioned static asset
  URLs so browser caches cannot mix old markup with new JavaScript.
- Reused density recorded during physical integration for final SOC serialization,
  removing a full second pass of CoolProp density calls.

## 2026-09-13 - Offline H2 property table runtime

- Profiled a two-second fast-mode case: 4.16 seconds total, dominated by repeated
  real-gas nozzle optimization and property calls inside numerical BDF Jacobians.
- Added a single-fluid hydrogen table generated offline from CoolProp HEOS,
  covering 0.01-120 MPa, 60-700 K, and 0.001-100 kg/m3.
- Added P-T forward interpolation and rho-u, P-h, and P-s inverse state paths so
  conserved mass-energy states and isentropic equipment calculations remain usable.
- Replaced direct process-runtime CoolProp calls with the table lookup; CoolProp is
  now a table-generation dependency and remains separately inside HyRAM.
- Added bounded exact-state caches to reuse repeated BDF/Jacobian lookups without
  quantization or altered physical equations.
- Random operating-envelope comparison produced maximum relative errors of 0.0115%
  for density, 0.0021% for enthalpy, 0.00046% for internal energy, 0.00044% for cp,
  0.0475% for rho-u pressure recovery, and 0.0010% for temperature recovery.
- The same two-second benchmark decreased from 4.16 seconds to 0.39 seconds after
  table and cache optimization, approximately 10.6 times faster after table load.
- A 30-second fast-mode run completed in 3.33 seconds with 31 streamed samples,
  approximately 9.0 times faster than real time on the development host.
- The API WebSocket verification received frames at 0, 1, and 2 simulated seconds
  before completion, then returned the stored final trajectory successfully.
- Separated process leak accounting from consequence cadence: leak mass and energy
  remain coupled every control step, while HyRAM updates use 5.0, 2.5, and 1.0
  seconds in fast, balanced, and precision modes respectively.

## 2026-10-08 - Prospective dual-valve release boundary

Status: implemented and frozen before any qualifying target-campaign outcome
trace was received; physical external validation remains pending.

Completed:

- Split the apparatus release boundary into independently prescribed upstream
  and terminal valve positions while preserving the legacy default behavior.
- Added precharged-line release support so a terminal valve can open against an
  already pressurized line without forcing the source-side valve to repeat the
  same travel law.
- Exposed both valve-position histories and retained the original
  `valve_opening_fraction` output as an upstream compatibility alias.
- Required the prospective manifest to declare whether its single synchronized
  valve trace belongs to the upstream or terminal valve; the evaluator now
  scores only that declared location and rejects ambiguous labels.
- Amended and re-hashed the no-fit protocol, evaluator, model and private
  manifest template before outcome access. The amendment does not change the
  external-validation readiness score until a qualifying untouched campaign is
  received and executed.

Verification:

- Dual-valve physics, conservation, evaluator, protocol integrity and IJHE audit
  regression tests passed (25 tests in the focused readiness run).
- The readiness audit remains 106 PASS, 10 FAIL and 8 PENDING out of 124 gates.

## 2026-10-08 - Closed-loop mixed-convection execution path

Status: implemented as a claim-bounded, post-outcome development diagnostic;
the production default and frozen external results are unchanged.

Completed:

- Added explicit validation-runner options for the mixed-convection tank model,
  declared inlet-nozzle diameter and a volume-preserving equivalent capsule.
- Refused missing, nonphysical or constant-UA geometry combinations before any
  experimental files are evaluated.
- Re-ran the 11 already-inspected comparison fills with a single declared 3 mm
  nozzle and 5:1 capsule aspect ratio without result-dependent parameter
  selection.
- Reduced aggregate mean pressure, temperature and SOC RMSE from 4.530 MPa,
  7.819 °C and 4.625 percentage points to 4.311 MPa, 7.156 °C and 4.380
  percentage points.
- Retained the constant-UA production default because the strict joint-screen
  result remained 2/11; controller and boundary-model error remains material.
- Stored the complete per-case output and a compact claim-boundary record so the
  expensive run does not need to be repeated during routine regression tests.

Verification:

- Mixed-convection geometry, CLI guard and claim-boundary focused tests passed.
- The complete repository regression suite passed: 1,002 tests, 18 dependency
  warnings, no failures.

## 2026-10-08 - Explicit cascade inventory and boundary diagnostic

Status: implemented; the post-outcome sensitivity is diagnostic only and does not
change the production default or an external-validation gate.

Completed:

- Replaced the hard-coded 0.35 m³ bank volume with independent low-, medium- and
  high-bank scenario inputs while preserving 0.35 m³ defaults.
- Recomputed initial bank mass from declared pressure, temperature and volume, and
  scaled the lumped wall inventory and heat-transfer conductance with aggregate
  vessel-module volume.
- Exposed the inputs through the API, remote operating settings and H2Protocol
  validation runner; invalid or incomplete volume triples are rejected.
- Re-ran the 11 already-inspected closed-loop cases from clean commit `471f94b`
  using one fixed 5.0 m³-per-bank source-inventory hypothesis and no volume grid.
- Engineering-screening passes increased from 2/11 to 6/11; mean pressure and SOC
  RMSE decreased by 0.173 MPa and 0.277 percentage points, while mean temperature
  RMSE increased by 0.356 °C. Paired bootstrap intervals included zero.
- Retained the 0.35 m³ reference default because public files do not disclose the
  connected storage topology, valve states, regulation or source temperature.

Verification:

- The clean diagnostic artifact records commit `471f94b`, a clean worktree and a
  SHA-256 digest of the complete per-case result.
- Focused scenario, API, runner and readiness-integrity tests passed.
- The complete repository regression suite passed: 1,011 tests, 18 dependency
  warnings, no failures.
