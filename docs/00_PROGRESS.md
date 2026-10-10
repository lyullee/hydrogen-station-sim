# Development Progress

## 2026-10-10 - Focused validation now uses the repository environment

- The priority runner now prefers `.venv`/`venv` before the process-wide
  Python interpreter. This prevents false collection failures when the global
  interpreter lacks the project's `fastapi`, `fluids` or `openpyxl` packages.
- The three high-impact tracks remain concurrent: P0 full-loop intake, P0 LLM
  evidence boundary, and P1 virtual safety/emergency response.
- A clean run now completes all 41 focused tests in about 8 seconds on this
  workspace; this is a software-verification result and does not promote any
  external-data gate.

Verification:

- `python scripts/run_priority_validation.py`: 41 passed, 2 dependency
  deprecation warnings, no collection errors.

## 2026-10-10 - Mixed-format split-channel full-loop intake

- The P0 intake now accepts station/vehicle pairs as CSV, XLSX, XLSM, or a
  mixed pair without first merging private files.
- Each side remains streamed independently and is checked against the same
  row-count, relative-time, jitter, protocol-phase and vehicle-boundary gates.
- Per-channel worksheet names are optional and are never written to the public
  freeze manifest. No external-validation gate was promoted by this change.

For a quick status check or focused parallel verification, use
`scripts/run_priority_validation.py`. It does not run the full regression and
does not alter any evidence gate:

```powershell
\.venv\Scripts\python.exe scripts/run_priority_validation.py --no-tests
\.venv\Scripts\python.exe scripts/run_priority_validation.py --output $env:TEMP\priority-validation.json
```

## 2026-10-10 - Priority tracks for faster validation progress

- The gap report now exposes three parallel execution tracks instead of a
  serial gate list: **P0 full-loop intake/scoring**, **P1 component-model
  repairs**, and **P2 review/publication**.
- The P0 path is the first high-impact check because the frozen evaluator is
  already implemented; once at least three synchronized events pass intake,
  the custodian can score them without waiting for unrelated component gates.
- Full regression is no longer a status check. It is reserved for code changes
  in the affected track; status checks use the privacy-bounded triage report and
  focused tests.
- No readiness gate was promoted by this workflow change.

## 2026-10-10 - Workbook intake for controlled full-loop files

- Added XLSX/XLSM support to the privacy-safe pilot and freeze workflow. The
  selected worksheet is read row by row, with the same numeric, time-axis,
  sampling and protocol-phase gates as CSV input.
- The workbook path, sheet rows and cell contents are not emitted; only the
  aggregate report and SHA-256 digest reach the freeze manifest.
- Combined-workbook and split-channel paths now have focused coverage; **13**
  intake/CLI tests pass. No external-validation gate was promoted.

## 2026-10-10 - Split-channel freeze workflow exposed in CLI

- Extended `freeze_privacy_safe_full_loop.py` with paired
  `--station-events`/`--vehicle-events` inputs. The CLI now performs the same
  streaming time-axis checks and creates a hash-only pre-access freeze
  manifest without requiring a merged raw file.
- Single-file intake remains backward compatible. Mismatched list lengths or
  missing paired arguments fail before a manifest is created.
- Focused intake and CLI tests pass **11 tests**; no external-validation gate
  was promoted.

## 2026-10-10 - Split-channel full-loop intake for real exports

- Added a streaming intake path for events delivered as separate station and
  vehicle CSV exports. It compares the two relative time axes row by row,
  rejects row-count/time mismatches, and preserves only aggregate quality flags
  and a combined digest.
- This removes a practical data-ingestion bottleneck without combining
  unrelated station and vehicle traces. A split bundle still needs common
  sampling, non-empty protocol phases, channel-role attestation and a frozen
  pre-access protocol before any full-loop claim can be made.
- Focused privacy-safe intake tests now pass **12 tests**; no readiness gate was
  promoted by this change.

## 2026-10-10 - High-impact full-loop intake gate tightened

- Prioritized the gate that directly determines whether the station-to-vehicle
  validation can be opened: privacy-safe event intake now checks non-empty
  `protocol_phase` values, per-event sample-period jitter, and a common sample
  interval across events before marking a full-loop protocol-freeze candidate.
- A bundle with vehicle channels but a broken or mismatched time axis now stays
  at `READY_FOR_PROTOCOL_FREEZE`; it cannot silently advance to
  `READY_FOR_FULL_LOOP_PROTOCOL_FREEZE`.
- This is a fail-closed data-quality improvement only. It does not change model
  parameters or claim readiness; the independent full-loop and human-review
  gates remain open.

## 2026-10-10 - Source-geometry-resolved Type-III follow-up candidate

- Connected the published Dickens inlet geometry (5 mm internal diameter,
  82 mm insertion) to the existing 5 mm mixed-convection sensitivity and
  recorded it as a reproducible follow-up candidate.
- The candidate reproduces a joint pass of the four frozen pressure and
  gas-temperature screens, but it is explicitly post-outcome and has **no**
  validation-gate effect. The original prospective Type-III result remains a
  retained negative (pressure pass, both temperature screens fail).
- The remaining protocol blockers are now explicit: the source and archived
  tank lengths differ (0.893 m vs 0.7451 m), and the archived case lacks the
  time-resolved inlet-temperature boundary. No runtime parameter was changed.
- Focused Dickens/blocker tests pass (8 tests). The overall readiness audit
  remains **127 PASS / 10 FAIL / 7 PENDING** and the full objective remains
  open.

## 2026-10-10 - Completion-gate revalidation after public-data sweep

- Re-ran the current evidence audit after the latest public-data search. The
  readiness counts remain **127 PASS / 10 FAIL / 7 PENDING**;
  `bounded_ijhe_submission_ready`, `full_user_objective_ready` and
  `goal_completion_permitted` remain false because the independent full-loop
  and human-review gates are still open.
- The additional CIP endpoint-table and DOE H2IQ report checks are retained as
  source-classification evidence only. Neither contains a rights-cleared,
  synchronized station-to-vehicle raw logger cohort, so no frozen validation
  decision or runtime parameter was changed.
- The latest complete regression run remains **1,257 passed / 20 warnings**;
  the focused post-search audit tests pass as well.

## 2026-10-10 - Figshare open-channel dispersion intake and full regression recheck

- Added a reproducible Figshare API intake for the CC BY 4.0 open-channel
  hydrogen-dispersion release (DOI `10.23642/usn.26117989.v2`). The manifest
  records 23 public files without committing raw rows; all 22 local experiment
  archives were size-checked and their CSV schemas were checked for 29
  concentration channels and monotonic flow and sensor time bases.
- Linked the intake manifest to the existing public concentration-proxy audit.
  The evidence remains explicitly component-level and cannot close the HRS
  full-loop, outdoor-distance, ESD or detector-transfer gates.
- Ran the complete project regression suite in `.venv` after the intake update:
  **1,257 tests passed in 276.85 s** with 20 dependency/physics warnings and no
  test failures. Running the global Python interpreter directly is unsupported
  because it does not contain the project dependencies; use
  `.venv\\Scripts\\python.exe`.

## 2026-10-09 - Local station-side cross-bundle pressure transfer diagnostic

- Added a frozen, privacy-bounded protocol that calibrates on one owner-controlled
  station-side pressure bundle and evaluates the fixed 4.5 MPa high-bank restart
  margin on a second bundle after explicit unit normalization.
- The transfer bundle produced 225 pressure cycles across 7 of 8 files; its
  median pressure drop was 5.45 MPa, the candidate was inside the p05-p95 range,
  and the relative error to the transfer median was 17.431193%.
- This is useful station-side corroboration only. It does not validate vehicle
  filling, full-loop behavior, leak/fire consequence predictions, accident
  frequency, safety limits or runtime parameter application.
- The raw local files remain outside the repository. Only aggregate results,
  protocol rules and privacy/claim-boundary metadata are committed.

## 2026-10-09 - Broader local archive connected with explicit HRS boundaries

- The local search found substantially more than the measured station bundle:
  18 adjacent hydrogen-city/pipeline event logs (2,411,774 rows), 19 related
  workbooks, a liquid-hydrogen-centre scenario collection, and a broader
  document archive screened at 38,528 machine-readable files and 12,804
  CSV/TSV headers.
- Added these aggregates to the privacy-bounded API and LLM evidence views.
  The assistant can now distinguish abundant adjacent process context from a
  synchronized station-dispenser-vehicle cohort. Raw rows, paths, headers,
  identifiers and dates remain excluded; automatic parameter application and
  full-loop claims remain disabled for the adjacent corpus.
- Regenerated the two source-hash audit records affected by the LLM evidence
  extension. Focused checks passed (8 tests), and the complete regression suite
  passed **1,156 tests** with 18 dependency warnings.

## 2026-10-09 - Full regression recheck after local-data evidence update

- Re-ran the complete Python regression suite after connecting the local
  station-data inventory and custodian-attestation boundary to the evidence
  documents.
- **1,138 tests passed** with 18 dependency deprecation/physics warnings and
  no test failures.
- The result verifies software and evidence-routing regressions only. It does
  not close the independent vehicle/full-loop, accident-casebook, expert-review
  or institutional-review gates that remain explicitly marked in the readiness
  audit.

## 2026-10-09 - Independent vehicle-channel recheck of the local archive

- Re-screened all 33 measured station CSV files in memory with an expanded
  synonym and abbreviation taxonomy covering vehicle, receptacle, dispenser,
  SOC, fueling and protocol fields.
- The archive remains 25 narrow nine-column files plus 8 wide 64-column files;
  the expanded screen found zero vehicle/dispenser and zero vehicle
  pressure/temperature candidates. This is a header-level negative result and
  still requires custodian confirmation; it does not expose headers or raw
  rows.
- Added the result to the privacy-bounded discovery artifact and the LLM
  evidence envelope. The full-loop gate remains closed while station-side
  validation continues.

## 2026-10-09 - Local HRS corpus inventory and validation boundary

- Rechecked the local collections and recorded a privacy-bounded corpus
  inventory in `research/local_hrs_corpus_inventory_2026_10_09.json` and its
  companion report.
- Confirmed that the owner-controlled station bundle is substantial: 33 files,
  4.749 GiB and 56,854,143 rows after duplicate exclusion. It supports
  station-side pressure, cascade, recharge and equipment-state checks.
- Counted 255 locally cached public machine-readable validation files totaling
  about 3.509 GB (decimal), including tank/refueling experiments and separate
  release, ignition, dispersion, detector and ventilation evidence.
- Kept the complete station-to-vehicle gate closed because no single local
  cohort has an independently attested common time base for vehicle/receptacle
  pressure, temperature, delivered mass or SOC together with station controls.
- Added regression checks for the inventory; the focused seven-test run passed.

## 2026-10-09 - Role-level attestation for the local station archive

- Rechecked the owner-controlled archive and preserved the privacy-bounded
  aggregate: 33 CSV exports, 32 unique payloads and 56,854,143 deduplicated
  rows.
- Added a role-level semantic record for two storage-pressure roles and two
  lifecycle-counter roles, and connected it to the readiness audit and LLM
  evidence envelope without publishing tags, dates, site identity or raw rows.
- Kept flow units, totalizer reset semantics and vehicle-side channels
  unverified; this improves station-side evidence but does not close the
  station-to-vehicle full-loop gate.

## 2026-10-09 - Local station archive connected to LLM evidence

- Completed a privacy-bounded inventory of the local station archive: 33 CSV
  files, 4.749 GiB, 59,272,300 physical rows and 56,854,143 rows after one
  exact duplicate payload was excluded.
- Confirmed that station-side evidence is substantial rather than sparse. The
  reviewed aggregate contains 16,770 ordered high-bank pressure cycles, 11,770
  paired medium/high episodes, 1,418 short-horizon pressure-forecast cases and
  733 conditional recharge-flow episodes.
- Added the aggregate record to the main and sensor LLM evidence envelopes.
  Interactive prompts receive only de-identified counts, readiness flags and
  claim limits; no local path, filename, header, timestamp, site identity or
  raw row is exposed.
- Kept vehicle-side/full-loop validation disabled because synchronized vehicle
  pressure, temperature, delivered mass or SOC is still absent from the
  attested archive. No runtime parameter or safety limit was promoted.
- Re-ran the complete regression suite: 1,072 tests passed with 18 warnings.

## 2026-10-08 - Prospective medium-to-high cascade-sequence holdout

- Froze the pressure-event pairing, eligibility and decision rules before
  viewing the joint medium/high sequence outcomes in the confidential archive.
- Retained 8,106 calibration and 3,664 holdout pressure-drawdown pairs from all
  12 matching histories. Holdout pair coverage was 70.3939%; 94.3777% of
  paired events followed the declared medium-to-high sequence, with a median
  handoff gap of 80 seconds.
- All frozen eligibility, coverage, sequence-stability and handoff-gap screens
  passed. The result supports the simulator's medium-to-high controller
  structure as a same-site observation.
- Kept vehicle-fill, low-bank, full-loop, independent-validation, safety-limit
  and runtime-parameter claims disabled because synchronized vehicle, valve
  and dispenser states are absent.
- The readiness audit is now 117 PASS, 10 FAIL and 7 PENDING; the complete
  regression suite passed 1,058 tests with no failures.

## 2026-10-08 - Chronology-corrected pressure-cycle holdout

- Preserved two negative pressure-cycle attempts and traced their zero-cycle
  result to strictly reverse-chronological source histories.
- Froze a third method before viewing chronologically ordered outcomes. It
  sorts timestamps ascending, resolves duplicate timestamps deterministically,
  and then applies the unchanged seven-sample causal median and cycle screens.
- Recovered 11,565 calibration and 5,205 holdout high-storage pressure cycles
  from all 12 matching histories. The holdout drop median was 4.6378 MPa; the
  existing 4.5 MPa restart margin differed by 2.97% and passed all frozen
  eligibility and stability screens.
- Classified this as same-site cross-format corroboration only. No runtime
  default, safety limit, vehicle-fill claim or full-loop validation status was
  changed.
- The complete regression suite passed after this update: 1,052 tests with no
  failures.

## 2026-10-08 - Confidential pressure/flow consistency boundary

- Recovered the two stable schemas in the 25 previously underused station
  history exports. The archive contains 58,618,833 one-second rows: 29,361,269
  pressure/flow-candidate rows and 29,257,564 temperature-candidate rows with
  99.7837% time-coverage overlap.
- A deterministic 600-row sample retained 97,709 diagnostic observations. All
  six non-cumulative pressure/flow candidate medians and all five
  temperature-like medians in the final 30% stayed inside the first 70%
  P05--P95 envelopes. The lower/medium/high pressure-candidate order held in
  99.9142% of samples.
- Kept flow/totalizer units, generic temperature roles and all runtime fitting
  disabled. The new result is longitudinal station-side evidence, not a
  vehicle-fill or consequence-distance validation.
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
- Cross-checked the reference compressor against 733 confidential recharge
  intervals selected by duration and compressor-load feedback. The conditional
  observed 10th--90th percentile was 6.951--9.916 g/s; the unchanged
  first-principles reference prediction of 8.689 g/s falls inside it. The
  runtime multiplier remains locked because flow units and calibration are not
  attested.
- Executed the pre-frozen 70/30 compressor/cooler thermal method as an explicit
  unattested mapping-hypothesis diagnostic over 653,442 one-second rows. All
  three component medians and the cooling-active temperature-drop median passed
  the frozen within-record stability screens, with no quality warning. Runtime
  and thermal-validation promotion remain disabled pending custodian
  attestation.
- The complete regression suite passed after this update: 1,037 tests with no
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

## 2026-10-10 - Privacy-bounded local schema screening made fault tolerant

Status: implemented; schema screening remains an intake aid and does not
promote any local file to an external-validation result.

Completed:

- Made the aggregate CSV schema scanner treat oversized or malformed fields as
  unreadable tables instead of aborting the entire local inventory.
- Prevented alternate-codec retries from classifying binary or malformed bytes
  as a false header after a CSV parser error.
- Re-screened the local `HRS_sim` material: 5 supported tabular files and 17
  tables were inspected, with no full-loop, station-recharge, vehicle-fill or
  synchronized full-loop candidate. The result contains aggregate counts only;
  source paths, headers, timestamps and rows are not persisted.

Verification:

- Controlled-schema tests passed (21 tests).
- This broad screen confirms that the current P0 blocker is still a missing
  synchronized, attested receiving-vessel/controller cohort rather than a
  scanner failure or lack of station-side files.

## 2026-10-10 - Public full-loop lead recheck expanded

Status: contact-only leads recorded; no unverified article or aggregate table
was promoted to a validation gate.

Completed:

- Rechecked public records for the UCI Gen-IV station and the Cal State LA
  back-to-back fueling study, both of which report real station/vehicle
  measurement channels and operator-log context.
- Added both records to the bounded lead catalogue with DOI, requested channel
  attestation, reuse-status and the minimum three-event intake request.
- Kept `full_loop_external_holdout_eligible=false` for both leads because no
  downloadable synchronized raw logger, channel dictionary and independent
  reuse terms were found.

Verification:

- Public-lead and validation-boundary tests passed (8 tests).
- The P0 gate remains correctly closed; the search produced better custodian
  targets, not a scientific validation result.
