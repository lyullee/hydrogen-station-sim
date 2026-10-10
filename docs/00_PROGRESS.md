# Development Progress

## 2026-10-10 - Repair readiness evidence digests after fast-lane changes

Status: implemented; the two stale source-hash records found by the readiness
audit were regenerated from the current code without changing any numerical
result, fit parameter, threshold or claim boundary.

- Refreshed the public Type-IV runtime calibration audit digest.
- Refreshed the public KHK accident-precedent routing audit digest.
- The authoritative audit is back to **127 PASS / 10 FAIL / 7 PENDING**;
  `bounded_ijhe_submission_ready=false` and
  `full_user_objective_ready=false` remain unchanged.

Verification:

- `tests/test_public_tank_runtime_calibration_audit.py`
- `tests/test_runtime_public_accident_precedents.py`
- `tests/test_ijhe_readiness_audit.py`: **5 passed**.

## 2026-10-10 - Make the fast-lane readiness result fail closed

Status: implemented; a completed diagnostic process is no longer presented as
usable scientific evidence when its screening result is negative or missing.

- `status` continues to mean process health for backward-compatible automation.
- New `readiness_status` is `PASS`, `BLOCKED`, `NOT_ASSESSED` or `FAIL` and is
  derived separately from the scientific screen.
- The current critical run therefore reports process `PASS` but readiness
  `BLOCKED` because `mc_tank_boundary` is **0/8**; this removes the ambiguity
  that caused repeated low-value reruns.

Verification:

- `tests/test_priority_diagnostics.py`: readiness separation checks passed.
- `scripts/run_priority_focus.py --priority critical`: process status remains
  compatible while the scientific blocker is surfaced explicitly.

## 2026-10-10 - Critical-first parallel execution checkpoint

Status: implemented; the critical work lanes were executed together instead of
waiting for a sequential full regression.

- Ran the P0 intake/evidence checks, the P1 virtual safety suite, and the
  bounded MC, Dickens, H2SAFE and Schefer diagnostics in one process run.
- The complete run finished in **12.2 s** and returned an execution **PASS**:
  19 P0 intake tests, 3 P0 LLM-boundary tests, 23 P1 safety tests and 5
  development diagnostics all completed.
- This is a process check, not a scientific promotion. The readiness decision
  is unchanged at **127 PASS / 10 FAIL / 7 PENDING** because the independent
  receiving-vessel/controller full-loop cohort is still absent.
- Work is now ordered by impact: P0 synchronized full-loop intake first, P1
  component failures in parallel, and P2 review/publication tasks independently.
  A slow broad regression is reserved for changes that actually touch those
  paths.

Verification:

- `scripts/run_priority_focus.py --priority all --max-workers 4`: **PASS** in
  12.2 s.
- Added the explicit `--priority critical` alias to both priority runners; it
  selects P0 and P1 together without requiring a broad regression command.

## 2026-10-10 - Run P0/P1 work in parallel and close the MC boundary probe

Status: implemented; the fast lane now confirms the high-impact tracks without
waiting for a full regression pass, and the remaining MC boundary variants were
checked before any model change was considered.

- P0 software/evidence checks and MC boundary diagnostics ran concurrently and
  completed in about **3.6 s**; both returned **PASS** as execution checks.
- P1 software/safety checks and the Dickens, H2SAFE and Schefer diagnostics ran
  concurrently and completed in about **11.1 s**; all three diagnostic runners
  returned **PASS** as process checks.
- The MC partial-station replay was compared under a constant source pressure,
  both published source-pressure channels, and the published protocol-pressure
  schedule. All four variants remained **0/8 joint screening passes**; mean
  pressure RMSE stayed about **3.48--3.79 MPa**, so no boundary variant was
  promoted or silently used to close the full-loop gate.
- The readiness audit remains **127 PASS / 10 FAIL / 7 PENDING**. This is a
  deliberate stop on low-value sequential tuning: the material blocker is still
  synchronized receiving-vessel/controller channels with independent provenance.

Verification:

- `scripts/run_priority_focus.py --priority P0 --max-workers 4`: **PASS**.
- `scripts/run_priority_focus.py --priority P1 --max-workers 4`: **PASS**.
- Four MC boundary probes: **0/8** each; no validation claim changed.

## 2026-10-10 - Recheck official public full-loop data sources

Status: no new eligible raw station-to-vehicle holdout was found; the search
branch is closed for now so model and safety work can continue in parallel.

- The current Zenodo HySaM release (`10.5281/zenodo.20590842`) still contains
  sampling-system workbooks without a vehicle-tank/controller boundary.
- The newer-looking FCEV fueling Zenodo record (`10.5281/zenodo.12737240`)
  contains an article PDF only. The DTU archive remains a Modelica/Matlab
  simulator reference, not measured time series.
- The official NREL HDVS and real-station publications remain data-request
  leads because synchronized raw rows, channel dictionaries and reuse terms are
  not publicly attached.

The full-loop gate remains closed honestly; the available H2P and station-side
traces continue through component diagnostics and LLM evidence grounding.

## 2026-10-10 - Repair Proust holdout metadata digests

Status: implemented; the Proust independent holdout's recorded evaluator and
runner digests were stale even though the implementation bytes and frozen model
had not changed since the original freeze commit.

- Corrected only the evaluator/runner SHA-256 fields in the frozen protocol and
  post-outcome sensitivity record, then refreshed the dependent protocol digest
  in the result records.
- Numerical observations, model parameters, screening thresholds and the
  negative 0/3 primary decision were left unchanged.
- This is an integrity repair, not a re-freeze or a validation promotion.

Verification:

- Proust protocol/result/sensitivity tests: **passed**.
- Readiness audit remains **127 PASS / 10 FAIL / 7 PENDING**; the Proust
  scientific gate remains a real FAIL because the fixed model passes 0/3
  primary series.

## 2026-10-10 - Refresh stale evidence-integrity hashes after code changes

Status: implemented; two audit failures caused by stale source digests are
resolved without changing any model result or readiness decision.

- Recomputed only the recorded SHA-256 values for the current Type-IV runtime
  calibration sources and the public accident-precedent routing sources.
- The audit returned to **127 PASS / 10 FAIL / 7 PENDING**. The remaining ten
  FAIL gates are scientific/component or full-loop gates, not stale-integrity
  artifacts.
- The negative validation results and the full-loop blocker remain unchanged.

Verification:

- `tests/test_ijhe_readiness_audit.py tests/test_llm_grounding.py`: **29 passed**.

## 2026-10-10 - Process-parallelize independent MC partial-station replays

Status: implemented; the slowest eight-case MC boundary diagnostic now runs
independent case integrations in bounded worker processes.

- `scripts/run_partial_station_validation.py` adds `--max-workers` and keeps
  `--max-workers 1` as a serial reproduction path.
- On the same workspace, the complete MC replay dropped from about **27.6 s**
  serial to **9.8 s** with four workers (about 2.8x faster).
- Aggregate metrics and every case metric were identical between serial and
  process-parallel runs. Output rows remain in deterministic lab-test order.
- This is a diagnostic execution change only; no frozen model, runtime
  parameter, validation result or readiness gate was changed.

Verification:

- Serial/parallel aggregate and case records: **identical**.
- `py_compile`, `git diff --check`: **passed**.

## 2026-10-10 - Isolate the MC upstream pressure boundary diagnostic

Status: implemented; measured source-pressure channels are now compared with
the frozen constant-boundary partial-station diagnostic and exposed to the
privacy-bounded evidence/LLM surfaces.

- Added `research/mc_source_pressure_boundary_diagnostic_2026_10_10.json` with
  aggregate-only results for the constant boundary and the two published MC
  source-pressure channels. No case identifiers, raw rows or local paths are
  exposed to runtime callers.
- The source-pressure runs remain development diagnostics: all 8-case screens
  are 0/8, and the full-loop external-validation gate is unchanged. The result
  narrows the high-impact unresolved boundary to upstream pressure/controller
  coupling rather than silently changing the runtime model.
- Added the same explicit claim fence to `local_evidence` and the LLM grounding
  envelope so responses can use the comparison without calling it validation.

Verification:

- `tests/test_validation_evidence_api.py tests/test_llm_validation_gap_grounding.py`:
  **3 passed**.
- Python compilation and `git diff --check`: **passed**.

## 2026-10-10 - Shorten the P1 transient diagnostic fast lane

Status: implemented; the Schefer line-transient sensitivity grid now evaluates
its independent valve-time-constant cases with two bounded workers.

- The baseline and five sensitivity replays own separate mutable EOS states, so
  they can run concurrently without changing the equations, solver tolerances,
  output ordering or evidence claim boundary.
- Two workers are used deliberately to avoid oversubscribing the numerical
  solver on operator machines. A local run dropped from about 15.5 s to about
  10.7 s while the aggregate metrics remained byte-for-byte identical to the
  previous serial diagnostic.
- This is a development-speed change only. It does not promote the Schefer
  holdout, alter runtime parameters or change any readiness gate.

Verification:

- `tests/test_priority_diagnostics.py`: **2 passed**.
- Serial-versus-parallel aggregate comparison: **identical**.

## 2026-10-10 - Combine the priority fast lanes

Status: implemented; P0/P1 software and physics checks can now start together.

- Added `scripts/run_priority_focus.py`, which composes the focused software/evidence
  runner and the bounded physics-diagnostic runner in one process-level fast lane.
- `--priority P0` runs only the highest-impact checks; `--priority all` keeps the
  independent P0/P1 tracks concurrent. The report preserves both runners' claim
  boundaries and does not alter model parameters or readiness gates.
- The combined command now defaults to `P0`, so an unqualified status run returns
  the blocking full-loop/evidence signal first; use `--priority all` when the
  broader component queue is needed.
- This avoids waiting for a serial “software first, diagnostics second” cycle while
  keeping the full regression suite available for broad changes.
- The priority-validation workflow now uses this combined command so CI exercises
  both tracks in the same fast lane.
- Diagnostic child processes now write to a temporary output directory during a
  priority run, so status checks no longer rewrite tracked research artifacts.

Verification:

- `tests/test_priority_focus.py`: 1 passed.

## 2026-10-10 - Surface the closed-loop diagnostic without promoting it

Status: implemented; the evidence API and LLM now share the same aggregate-only
development result.

- Added a privacy-bounded `public_closed_loop_calibrated_diagnostic` inventory entry
  for the 11-case post-outcome comparison (1/11 screening passes).
- The projection contains only aggregate error means and the explicit claim fence;
  it cannot be treated as an independent holdout, runtime calibration, or safety
  validation.

- The same evidence surface now exposes the MC Type-IV geometry sensitivity:
  capacity-EOS reached 4/8 joint screens versus 0/8 for the frozen Tables-Method
  volume. Rule selection remains prohibited until an untouched vessel-geometry
  holdout is available.
- A separate MC boundary diagnostic confirms the published SOC channel agrees with
  the co-located pressure/temperature EOS (8/8 diagnostic screens; maximum RMSE
  0.33 percentage points). The remaining MC failure is therefore treated as a
  tank-boundary/geometry or thermal-model issue, not an SOC-definition issue.
- The source-grounded Dickens follow-up candidate is now included in the same LLM
  evidence surface: the 5 mm/82 mm inlet geometry passes the four diagnostic
  screens, while tank-length interpretation and time-resolved inlet temperature
  remain explicit prerequisites for a new prospective run.

## 2026-10-10 - Inspect scientific containers in local data discovery

Status: implemented; MATLAB/HDF5 channel-name screening completed without
persisting numeric arrays.

- The privacy-safe scanner now optionally reads MATLAB variable metadata via
  `whosmat` and bounded HDF5 group/dataset names. Scientific inspection is
  opt-in and aggregate-only, like the existing XLSX header inspection.
- The project archive scan covered 86 scientific containers and the adjacent
  document workspace covered 1,323. Neither produced a synchronized full-loop
  candidate; the project still has 8 partial boundary bundles without protocol
  phase evidence.
- Corrupt or mixed-version scientific files are counted as per-file parse misses
  and no longer abort the complete scan. No path, filename, variable name or
  numeric value is written to the report.

Verification:

- `tests/test_local_workspace_candidate_scan.py`: 9 passed.

## 2026-10-10 - Run high-impact diagnostics concurrently

Status: implemented; bounded P0/P1 development diagnostics now have a parallel
fast lane.

- Added `scripts/run_priority_diagnostics.py` to run the measured-boundary MC
  tank replay and independent P1 physics diagnostics concurrently. A slow
  release or spatial diagnostic no longer blocks unrelated model work.
- The runner records only process status, duration and sanitized output tails.
  It does not promote a readiness gate, change runtime parameters, or persist
  raw measurements.
- The Schefer line-transient sensitivity uses a diagnostic-only solver profile;
  its baseline metrics stay within 0.04 percentage points of the prior strict
  run while reducing that five-case diagnostic from about 101 s to about 17 s.
- Use `--priority P0` or `--priority P1` when focusing on the highest-impact
  track, or `--list` to inspect the queue without running it.

Verification:

- `tests/test_priority_diagnostics.py`: 2 passed.

## 2026-10-10 - Add split-log discovery and template exclusion

Status: implemented; split candidates remain zero in the scanned archives.

- The local discovery scanner now checks for matching station/vehicle file
  pairs in the same directory using only an in-memory normalized stem. It
  reports an aggregate lead count without emitting paths, filenames or
  headers.
- Static `template`, `schema` and `example` files are excluded from measured
  trace candidates so an input template cannot inflate the apparent data
  inventory.
- Re-running both local archives found **0 split-pair leads** and **0 eligible
  full-loop candidates**. The result remains discovery-only until a custodian
  attests units, clock alignment, boundary roles and reuse rights.

Verification:

- Workspace scanner tests: **5 passed**.

## 2026-10-10 - Broaden explicit full-loop logger aliases

Status: implemented; ambiguity and unitless boundary guessing remain blocked.

- Added unit-qualified aliases commonly emitted by logger exports, including
  `time (s)`, `pressure (MPa)`, `temperature[C]`, `flow[g/s]`,
  `operation_state`, and vehicle-side pressure/temperature labels.
- The intake still rejects generic unitless `pressure` and `temperature`, and
  duplicate aliases still fail closed. No source header or raw row is emitted.

Verification:

- Full-loop intake suite: **14 passed**.

## 2026-10-10 - Re-scan the available local archives for the P0 loop gate

Status: scan completed; no unverified data was promoted.

- Re-scanned the local project archive and the larger private data workspace
  with the privacy-bounded candidate scanner. The larger scan covered 47,061
  machine-readable files and 14,989 CSV/TSV headers; the project archive
  covered 84 files.
- Both scans returned **zero eligible full-loop candidates**. They contain
  many station-side pressure/temperature/flow/control-like headers, but no
  file or attested file pair closes the synchronized station/dispenser to
  receiving-vessel boundary with protocol state.
- The scan records retain only aggregate counts and the required attestation
  fields. They do not publish paths, filenames, headers or measured values.

Evidence:

- `research/local_docudata_candidate_scan_2026_10_10.json`
- `research/local_hrs_sim_candidate_scan_2026_10_10.json`

## 2026-10-10 - Prepare the accident-casebook review packet

Status: machine preparation complete; human gates remain intentionally open.

- Rebuilt the 24-case HIAD holdout coordinator packet and verified that the
  same casebook hash, case count, prescreen CSV, HTML review form and machine
  preflight are carried through the handoff.
- The machine prescreen flags 16 high, 6 medium and 2 low hindsight-leakage
  candidates and suggests 37 sentence removals. These are advisory only; the
  source casebook was not modified automatically.
- The packet is ready for a qualified non-rating coordinator. Response
  collection remains fail-closed until the coordinator review and institutional
  ethics/exemption determination are recorded.

Verification:

- Reviewer packet audit: **all machine checks passed**.
- Human review status: **ready for handoff; response collection blocked**.

## 2026-10-10 - Refresh readiness audit after runtime integrity update

Status: implemented; the audit is current and still fail-closed.

- Regenerated the runtime Type-IV calibration integrity record after the
  explicit full-loop channel-alias change. This removes a stale source-hash
  mismatch that made the readiness audit report a false `FAIL`.
- The current readiness remains **127 PASS / 10 FAIL / 7 PENDING**. The open
  P0 gate is still the absence of three independently sourced,
  synchronized station-to-receiving-vessel/controller events; no scientific
  claim was promoted by refreshing the audit.
- The full audit is retained in `docs/IJHE_READINESS_AUDIT.md` and the
  machine-readable result in `research/ijhe_readiness_audit.json`.

Verification:

- IJHE audit regression: **2 passed**.
- Priority validation: **44 focused tests passed** in about **5 s**.

## 2026-10-10 - Remove full-loop intake naming friction on the P0 path

Status: implemented; safety and validation gates remain fail-closed.

- The privacy-safe full-loop intake now recognizes a small, explicit set of
  common engineering aliases for elapsed time, station/dispenser pressure,
  delivered-gas temperature, mass flow, protocol phase, and vehicle/receptacle
  pressure and temperature. This lets a custodian run the quality screen
  without first renaming every column.
- Generic names such as `pressure` and `temperature` are intentionally not
  inferred. If two headers could represent the same role, intake reports an
  ambiguity and stops; it never silently chooses a boundary.
- Raw headers remain outside the report. The public result contains only
  canonical channel-presence flags and an alias-count diagnostic. No evidence
  gate, model parameter, or external-validation claim was promoted.

Verification:

- Full-loop intake and CLI suites: **18 passed**.

## 2026-10-10 - Make the balanced control cadence the operator default

Status: implemented; precision mode remains available.

- The API and remote now default to a 0.5 s control period. The existing 1.0 s
  fast mode and 0.2 s precision mode remain selectable.
- This changes only the unspecialized operator default. Fault, relief, vent and
  cooling events still use the event-aware solver path, and no safety threshold
  or physical coefficient changed.
- A local smoke comparison after warm-up measured a 10 s nominal run at about
  2.8 s with 0.2 s control and about 2.0 s with 0.5 s control. These are local
  development timings, not a real-time performance guarantee.

## 2026-10-10 - Remove scalar property lookup allocations from the solver hot path

Status: implemented; property/restriction regression suite passed.

- Replaced scalar `searchsorted` calls in the dispenser choking-ratio lookup and
  density-to-pressure inversion with monotone `bisect` lookups.
- The tabulated hydrogen table remains the numerical source and the bracket,
  endpoint, and interpolation rules are unchanged; this only removes temporary
  NumPy scalar allocations during ODE right-hand-side evaluations.
- A 15-second reference run completed in about **4.7 s** on the local runtime
  (HTTP polling included). A prior 60-second smoke run took about **11.6 s**;
  these timings are reported as separate smoke baselines, not as a controlled
  benchmark claim.

Verification:

- Restriction-table, process-operation, and frame-cursor suites: **29 passed**.

## 2026-10-10 - Avoid duplicate frame-result serialization

Status: implemented; continuous-stop alignment regression passed.

- Finite and continuous runs now build their API result from the retained,
  unit-converted monitor frames that already drive the UI. The legacy state
  serializer remains available for direct callers and fallback runs.
- This removes redundant gas-state reconstruction at shutdown while preserving
  HAZOP frames, detector series, trend data, leak series, event logs, summary
  values, and impact values.

Verification:

- Continuous stop/result alignment: **1 passed**.

## 2026-10-10 - Remove long-run telemetry scan bottleneck

Status: implemented; focused API/stream regression passed.

- Continuous websocket delivery and the HTTP fallback no longer filter the
  entire retained frame history on every polling tick. Because frame sequence
  numbers are monotonic, delivery now walks back only across newly appended
  frames and catches up once if the bounded replay window has rolled over.
- The 3D risk overlay also stopped deep-copying the full latest HAZOP tree on
  every refresh. Published frames are append-only snapshots, so the endpoint
  can read the latest frame directly while holding the job lock.
- Its 30-second cache now invalidates immediately for ESD, active-fault,
  HAZOP-rule, relief-valve, or release-state transitions, while concurrent
  overlay requests for the same job share one in-flight calculation.
- Continuous websocket delivery now coalesces quiet intermediate frames at
  the display boundary while preserving every ESD, leak, relief, dispatch,
  recharge, alarm, and process-state transition. The complete physical frame
  history remains available through the HTTP cursor and final result APIs.
- On job completion the browser replaces the live projection with that full
  result, so trend replay and CSV export retain every physical sample even
  when the live view used coalesced frames.
- This changes transport and presentation overhead only. Physical integration,
  HAZOP sampling, safety actions, and stored replay frames are unchanged.

Verification:

- HAZOP/API/process-operation suite: **70 passed**.
- Added cursor and risk-signature regression coverage for incremental delivery,
  trimmed-window recovery, immediate safety-state invalidation, and live-frame
  coalescing.

## 2026-10-10 - Direct operator command bridge

- Added a deterministic command-intent layer to both the main direct assistant
  and selected-sensor direct assistant. Explicit requests such as ESD trip,
  process stop, vehicle-2 fueling stop, zone evacuation and ventilation control
  now return reviewed virtual-action proposals instead of only a status report.
- Proposals are confirmation-gated: the assistant never mutates the simulation
  from natural language. The existing virtual safety endpoint performs the
  command, actuator movement and feedback verification after the operator
  clicks the rendered action button.
- Explicit command turns bypass the generative completion wait after the
  deterministic snapshot is ready, so the buttons appear without waiting for
  the slower LLM narrative. Ordinary questions still use the selected direct
  assistant and emergency impact assessment path.
- Status questions do not produce command candidates. Main and sensor panels
  render the same action buttons and report the resulting command/feedback in
  the existing safety log.

Verification:

- Direct Q&A, sensor workbench, grounding and readiness-integrity tests:
  **56 passed**; Node stream/separation/automatic-analysis tests: **6 passed**.

## 2026-10-10 - High-impact solver and telemetry hot-path reduction

- Kept the validated table equations and API output cadence, but replaced
  scalar `clip`/`searchsorted`/`interp` wrappers in the hydrogen property
  lookup with allocation-free scalar paths. The `rho,u` inverse now uses a
  four-update Newton cap because the table-provided initial guess converges in
  two updates across the operating envelope; boundary and round-trip checks
  remain within the existing numerical tolerances.
- Kept every physical sample and HAZOP frame. The operator-facing summary and
  station pressure forecast are refreshed at most once per simulated second,
  with immediate refresh on ESD, fault, relief, detector-band or HAZOP-rule
  changes. This reduces repeated advisory work without delaying safety state
  transitions or changing the controller.
- Refreshed the privacy-safe Type-IV runtime integrity record after the API
  source hash changed. No experimental rows or external-validation claims were
  modified.

Verification:

- Focused core, HAZOP, pressure-forecast, API, and live-fault tests: **81 passed**.
- Full regression after the change: **1275 passed, 1 stale integrity failure**;
  regenerating the runtime integrity record resolved that failure, and the
  readiness-audit test then passed **2/2**. The original 1275 passing tests are
  retained; the remaining evidence gates are unchanged.
- A local 10 s operator-model spot run at the default 0.2 s control period
  measured roughly 4× simulated time per wall-clock second after warm-up; exact
  speed remains CPU- and scenario-dependent.

## 2026-10-10 - Parallel priority pass: live public-catalogue access boundary

- Rechecked the NBSDC liquid-hydrogen refueling-station catalogue through its
  current metadata and file-tree endpoints. The record still exposes seven
  files (about 42 MB) and a one-second, real-station monitoring scope with
  pressure, temperature, flow, dispensed mass, current, frequency, level and
  volume roles.
- Probed all six numerical workbooks/CSV files independently. Each returned
  the portal's HTTP 200/JSON 403 application-required response; only the
  description file was downloadable. No numerical row was copied, opened or
  used for fitting. The result is now preserved in the bounded recheck's
  `live_recheck` section and the data-coverage summary.
- This closes the repeated public-search loop for this candidate: it is a
  high-priority custodian request, not a validation pass. The three execution
  lanes remain independent so station-side model repairs and LLM/publication
  work do not wait for the full-loop access request.

Verification:

- `scripts/recheck_nbsdc_liquid_hrs_access.py` completed against the live
  catalogue; six numerical probes returned portal code 403 and
  `raw_numerical_files_obtained=false`.
- The focused priority command remains the fast status/verification path;
  full regression is reserved for broad code changes.

## 2026-10-10 - Parallel runtime evidence replay refreshed

- Re-ran the privacy-bounded station-side integration audit from the existing
  frozen aggregates. Pressure-boundary replay, medium/high cascade sequence
  context and recharge-pressure forecast remain supported; the negative
  lifecycle-counter result remains explicitly retained.
- Re-ran the canonical HIAD-to-runtime response handoff independently. All
  **9/9** executable incident families reached the expected response plan and
  complete recognition/immediate/stabilize/restart/prevention guidance.
- No raw rows, source identity, runtime defaults or external-validation gates
  were changed. The attempted thermal-effects command was fail-closed because
  the external MAT archive is not present locally; its prior evidence artifact
  was restored rather than replaced with an empty result.

Verification:

- `tests/test_confidential_station_side_integrated_validation.py`,
  `tests/test_hiad_runtime_response_handoff.py` and
  `tests/test_ijhe_readiness_audit.py`: **5 passed**.

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
- GitHub Actions now runs the same focused P0/P1 command from a clean Python
  3.12 environment on pushes and pull requests to `main`.

## 2026-10-10 - Readiness hashes refreshed after evidence updates

- Rebuilt the public Type-IV runtime-calibration audit and public accident-
  precedent routing audit after their source files changed. The previous
  failures were stale hash records, not model or routing failures.
- Synchronized the research and manuscript readiness snapshots. The current
  authoritative count is 127 PASS / 10 FAIL / 7 PENDING; the remaining FAIL
  gates are genuine physics/full-loop or governance gaps.

Verification:

- Readiness, tank-runtime and accident-routing tests passed (5 tests).

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

## 2026-10-10 - Public-search branches closed and P0 intake re-centered

- Screened the public HSR-Rig-Project and Figshare 20928025 leads. They are now recorded as bounded component/design context, not station-to-vehicle validation.
- Closed this search branch so development time is not spent repeatedly collecting pressure/temperature tables that lack the receiving-vessel and controller boundary.
- Re-centered the next high-impact action on the privacy-safe three-event custodian intake; P1 component repairs and P2 review remain independent parallel tracks.

## 2026-10-10 - Local workspace priority scan

- Re-scanned the local project/data roots with privacy-bounded discovery and controlled schema checks. The roots contain substantial station-side material, but no attested synchronized station-to-vehicle full-loop candidate.
- The private station archive remains immediately usable for station-side pressure, cascade and recharge diagnostics; it is not vehicle-side validation.
- P0, P1 and P2 work are therefore kept independent: three-event receiving-vessel intake, station-side/model repairs, and LLM/HIAD/publication work proceed without waiting on one another.

## 2026-10-10 - Parallel priority validation runner executed

Status: implemented; this is a software-regression checkpoint and does not
promote any external validation gate.

Completed:

- Ran the P0 full-loop intake checks, P0 LLM evidence-boundary checks and P1
  virtual-safety/response checks concurrently through
  `scripts/run_priority_validation.py`.
- All three tracks passed (15 + 3 + 23 focused tests) in 8.155 seconds of
  wall-clock time. The run is captured in
  `research/priority_validation_run_2026_10_10.json`.
- Kept the readiness decision unchanged at 127 PASS / 10 FAIL / 7 PENDING;
  the synchronized receiving-vessel/controller cohort remains the single P0
  full-loop blocker. No external claim, frozen protocol or private row was
  changed.

Verification:

- The focused LLM, SAGA contract, emergency-response and readiness-integrity
  suites passed: 45 tests, 2 dependency deprecation warnings.

## 2026-10-10 - NREL H2FillS geometry pressure-bias diagnostic

Status: evidence recorded; no frozen gate or production default was promoted.

Completed:

- Replayed the local, hash-identified NREL H2FillS 2022 HDVS Type-IV sample
  through the existing tank screen: seven common-clock tank traces, 351 rows
  each.
- The legacy reference geometry produced 0/7 screening passes, pressure RMSE
  6.164 MPa and final pressure error -8.681 MPa.
- A declared-capacity, tabulated-EOS geometry sensitivity produced 7/7 passes;
  the no-volume-fit variant reduced pressure RMSE to 0.496 MPa. This is a
  post-access diagnostic, so it is retained as a model-repair lead rather than
  a confirmatory validation result.
- Added the privacy-safe summary to
  `research/nrel_h2fills_geometry_diagnostic_2026_10_10.json` and its Markdown
  report. The raw workbook remains local and is not redistributed.

Next independent action:

- Freeze a new capacity-EOS geometry protocol before outcome access, then test
  it on a disjoint tank cohort and a synchronized station-to-receiving-vessel
  cohort before changing the runtime default.

## 2026-10-10 - SAE J2601 capacity-EOS sensitivity boundary

Status: diagnostic evidence recorded; no production or readiness promotion.

- Replayed all 36 public Powertech Labs SAE J2601 Tables Method traces with
  capacity-EOS geometry and uncalibrated station/thermal boundaries.
- The replay produced 0/36 engineering-screening passes: mean pressure RMSE
  25.339 MPa, temperature RMSE 17.589 °C and SOC RMSE 32.049 percentage
  points. Most traces stopped on the declared gas-temperature limit.
- This separates the next P1 repair work into protocol pressure-ramp/controller
  semantics, dispenser/precooler calibration and thermal stop-boundary handling.
  Capacity geometry alone is not promoted as a system fix.
- A privacy-safe summary is stored in
  `research/h2protocol_capacity_eos_sensitivity_2026_10_10.json` with the
  corresponding Markdown report.

## 2026-10-10 - Validation geometry provenance aligned with runtime builder

Status: implemented and smoke-tested.

- The SAE J2601 validation runner now passes `vehicle_geometry_basis` and both
  declared vehicle capacities into `ReferenceScenario` when the command uses
  `--geometry-basis capacity_eos`. The report label and the scenario builder
  therefore use the same geometry rule.
- This removes an ambiguity where a capacity-EOS volume was calculated by the
  runner but the builder remained in reference-volume mode. Explicit fitted
  multipliers remain explicit and are not silently changed.

Verification:

- One public H2P-L03 capacity-EOS smoke replay completed successfully.
- The NREL validation, public-validation and priority-runner suites passed:
  33 tests.
- After the wiring change, all three parallel priority tracks passed again in
  7.053 seconds; the run is captured in
  `research/priority_validation_run_2026_10_10_after_geometry_wiring.json`.

## 2026-10-10 - Continuous-monitoring forecast cost bounded

Status: implemented; focused regression passed.

- The live API keeps the complete frame history for replay, but the causal
  station-pressure advisory now receives a bounded recent window sized from
  the requested solver step. This removes the previous repeated full-history
  scan that made long continuous runs grow toward O(n²) forecast work.
- The bound is an internal performance guard only. It does not alter process
  states, controller commands, safety limits, ESD behavior, or the forecast
  claim boundary.

Verification:

- `tests/test_station_pressure_forecast.py`, `tests/test_integration.py` and
  `tests/test_priority_validation.py`: 8 passed.
- The three independent priority tracks remain concurrent and pass in 6.857 s;
  no readiness gate was promoted by this optimization.

Follow-up hardening:

- The forecast helper itself now walks chronological list inputs backwards and
  stops after the causal ten-second prefix. This keeps direct replay/API
  callers safe even when they provide the full retained trajectory instead of
  the live bounded deque.
- A regression test covers a 100,011-frame history and confirms that only the
  recent causal window is selected.

Focused UI/control regression after the performance change:

- Node UI suites: 15 passed (analysis stream, provider/API separation, flow
  routing, risk range state and periodic-analysis controls).
- Python operation/safety suites: 90 passed (normal-operation alarm policy,
  virtual safety, HAZOP and process operations).

## 2026-10-10 - Event-aware solver selection for nominal operation

Status: implemented; event and physics regressions passed.

- The default no-event simulation path no longer forces BDF with a dense
  numerical Jacobian for every control period. It uses the existing
  non-reentrant-safe LSODA path; BDF remains selected whenever fault, relief,
  vent or cooling events make the right-hand side discontinuous.
- A 60-second API smoke run completed in 15.08 s after the change (the earlier
  same-shape run took 20.5 s). This is a runtime measurement, not a claim of
  real-time performance at every model configuration.
- No physics constants, safety limits or event semantics were changed.

Verification:

- Core, integration, process-operation, virtual-safety and emergency-response
  suites: 57 passed.

## 2026-10-10 - Cache repeated isentropic property queries

Status: implemented; public, HyRAM and safety regressions passed.

- The tabulated EOS now caches the deterministic `(pressure, entropy)` flow
  property pair used repeatedly by the nozzle/choking calculation. It avoids
  recomputing the same interpolation during solver stages without changing
  the table, interpolation rule or physical output.
- In a 10-second nominal replay, the measured wall time dropped from 3.107 s
  to 2.426 s. A 60-second API smoke run completed in 12.91 s after both
  runtime optimizations.

Verification:

- Core, API integration, HyRAM adapter parity, public validation, virtual
  safety and emergency-response suites: 60 passed.

## 2026-10-10 - NREL HDVS high-flow data lead added

Status: evidence lead recorded; no validation gate promoted.

- The official DOE/NREL heavy-duty fueling report describes an 82.3 kg HDVS
  high-flow fill and exposes the relevant channel family: station/hose/
  receptacle/HDVS pressures and mass-flow rate.
- No rights-cleared common-clock raw logger archive was located, so the source
  is recorded as a custodian-data request lead rather than treated as an
  external holdout. The full-loop gate remains open.
- Added the lead to
  `research/public_full_loop_search_recheck_2026_10_10.json` with its claim
  limit and privacy-safe channel list.

## 2026-10-10 - Calibrated J2601 confirmation diagnostic recorded

Status: development diagnostic recorded; no readiness gate or production default
changed.

- Replayed 11 already-consumed public J2601 cases with the existing tank, flow
  and thermal development calibrations, capacity-EOS geometry and mixed-
  convection vehicle model.
- Compared with the same 11-case internal baseline, mean pressure RMSE changed
  4.530 → 4.190 MPa and mean final-SOC RMSE 4.625 → 4.282 percentage points;
  mean temperature RMSE changed 7.819 → 7.710 °C.
- The engineering screen passed 1/11 cases, so the result is retained as a
  repair signal and explicitly cannot be promoted to an independent holdout,
  field-safety claim, SAE conformance or production-parameter change.
- The boundary and source hashes are recorded in
  `research/closed_loop_calibrated_confirmatory_diagnostic_2026_10_10.json`;
  the detailed report is
  `research/CLOSED_LOOP_CALIBRATED_CONFIRMATORY_DIAGNOSTIC_2026_10_10.md`.

Verification:

- The new diagnostic-boundary regression and readiness/data-summary checks pass.

## 2026-10-10 - Ground calibrated diagnostics without promoting claims

Status: implemented; provider-grounding and full regression suites passed.

- The LLM evidence manifest now exposes the 11-case calibrated closed-loop
  comparison as a compact development diagnostic with its aggregate metrics.
- The manifest carries explicit `claim_supported=false` and
  `promotion_prohibited=true` flags plus the original claim boundary, so the
  provider can use the result as context without calling it an independent
  holdout, field-safety validation, SAE conformance result or production
  parameter change.
- The existing frozen station-to-vehicle holdout boundary and readiness gates
  are unchanged.

Verification:

- Focused LLM-grounding suite: 28 passed.
- Full regression suite: 1276 passed, 20 warnings.

## 2026-10-10 - Keep automatic LLM analysis opt-in

Status: implemented; UI regression passed.

- Periodic and alarm-triggered LLM analysis now starts **OFF** unless the
  operator explicitly enables the toggle. Previously, a new browser session
  with no saved preference implicitly enabled both paths, which could issue
  unsolicited requests during live frames and make the interface feel slow.
- Manual questions and virtual evaluations remain available while automatic
  analysis is OFF. An explicit `on` preference still enables the existing
  periodic/alarm behavior; an explicit `off` preference remains respected.

Verification:

- Node UI suites: 16 passed, including a regression for the no-preference
  default.

## 2026-10-10 - Throttle live monitor repaint and stop canvas resets

Status: implemented; JavaScript syntax and UI regression suites passed.

- The wall monitor and selected-node trend renderer no longer redraw on every
  28–35 ms simulation frame. They coalesce updates to a 120 ms presentation
  cadence while keeping resize and explicit selection updates immediate.
- Trend canvases retain their backing buffer when their pixel dimensions have
  not changed. Repeatedly assigning `canvas.width`/`height` had been clearing
  the drawing surface during playback, which caused visible flicker and extra
  raster work.
- This is presentation throttling only; the simulation frame index, stored
  telemetry and safety calculations are unchanged.

Verification:

- `node --check web/monitor-wall.js` and `web/node-monitor.js` passed.
- Node UI suites: 16 passed.

## 2026-10-10 - Strengthen full-loop intake phase evidence

Status: implemented; privacy-safe intake and grounding regressions passed.

- Privacy-safe station/receiving-vessel intake now records only aggregate phase
  evidence: distinct phase count, transition count, start-marker presence and
  terminal-marker presence. Raw phase labels are not emitted.
- A synchronized vehicle-boundary bundle with a single repeated phase can no
  longer become a full-loop protocol-freeze candidate. Each event must show a
  multi-phase sequence and a start marker before the pre-access freeze path is
  opened.
- Terminal markers remain an explicit advisory field because custodians use
  different stop/complete conventions; they are visible to the reviewer before
  the scoring protocol is frozen.

Verification:

- Full-loop intake/CLI/freeze/registry checks: 30 passed.
- LLM grounding and evidence API checks: 31 passed.

## 2026-10-10 - Throttle 3D operator-card repaints without slowing physics

Status: implemented; 3D module syntax and UI regression passed.

- The 3D scene, animated routes, accident effects, hose state and risk-range
  updates remain frame-driven.
- Operator cards, instrument canvases, CCTV labels and monitor summaries now
  repaint at most every 120 ms, with immediate repaint on ESD, fault, relief,
  recharge and vehicle-flow transitions.
- This removes repeated layout/raster work that caused visible flicker in
  recordings while preserving the underlying simulation frame and safety
  state.

Verification:

- `node --check web/station3d.js` passed.
- Node UI suites: 16 passed.

## 2026-10-10 - Compress large result snapshots without buffering streams

Status: implemented; API regression suite passed.

- Added Starlette `GZipMiddleware` for regular JSON responses above 1 KiB.
  Finite simulation results contain dense frame, trend, detector and event
  arrays, so this reduces transfer and browser parse pressure without changing
  the simulation or result schema.
- Starlette's event-stream exclusion remains in effect, so LLM token streams
  and live simulation streaming are not buffered or compressed.

Verification:

- `/api/health` returned `content-encoding: gzip` for the JSON response.
- API/integration/Hazop/header/initial-fill suite: 72 passed.
- Public Type-IV runtime calibration audit: `runtime_match=true`.
## 2026-10-10 - Close the local spreadsheet/full-loop discovery gap

Status: implemented; privacy-bounded scanner regression passed.

- The local candidate scanner can now inspect a bounded header window from XLSX
  files when `--inspect-spreadsheets` is explicitly enabled. Workbook values,
  paths, filenames and headers remain in-memory only and are never persisted.
- A single export containing synchronized station/dispenser and receiving-vessel
  channels is now counted as a `full_loop_timeseries_candidate`; this was
  previously hard-coded to zero, so a valid combined export could be silently
  missed. Split-file candidates remain attestation-only.
- The opt-in scan of the HRS project (84 machine-readable files) and the local
  document folder (47,062 files, including 232 XLSX files) found zero
  synchronized full-loop candidates and zero station/vehicle split pairs. The
  P0 data gate therefore remains open for the same reason: no attested
  station/vehicle/controller time-aligned trace has been supplied.

Verification:

- `tests/test_local_workspace_candidate_scan.py`: 7 passed.
- Both privacy-safe scan artifacts were regenerated with spreadsheet inspection
  enabled; no source path, filename, header or measurement value was emitted.

## 2026-10-10 - Separate public partial-loop evidence from protocol-complete data

Status: implemented; public-data discovery now narrows the P0 request.

- The scanner now recognizes a single export that contains source/supply
  pressure, receiving-vessel pressure/temperature and flow but lacks a
  controller phase channel as `boundary_bundle_missing_protocol_candidate`.
- The repository’s public-data scan found 8 such candidates, corresponding to
  the downloaded MC bench traces. These traces are useful for source-to-tank
  process development, but they remain below the full-loop gate because the
  controller phase transitions and independent protocol provenance are absent.
- The full-loop count remains 0 by design; no claim is promoted from a partial
  boundary bundle. The next data request is now narrowly defined as the phase
  transition/controller log aligned to those public traces, or three new
  events containing that channel.

Verification:

- `tests/test_local_workspace_candidate_scan.py`: 8 passed.
- Privacy-safe repository scan: 2,084 machine-readable files, 8 partial-loop
  candidates, 0 full-loop candidates, and 0 split-file pairs.

## 2026-10-10 - Feed scientific-container discovery into LLM evidence

Status: implemented; evidence and grounding regressions passed.

- The MATLAB/HDF5 header scan is now surfaced through the same privacy-bounded
  evidence envelope used by LLM responses. It reports aggregate screening only:
  1,409 scientific file headers screened across the two local archives, 8 partial
  boundary candidates, and 0 full-loop candidates.
- No paths, filenames, headers, identifiers, raw rows or measurement values are
  exposed, and the evidence explicitly prevents runtime calibration or a
  full-loop validation claim.

Verification:

- Local evidence, validation API and LLM grounding suites: 31 passed.

## 2026-10-10 - Skip remote HAZOP cross-checks for routine status questions

Status: implemented; direct-QA and sensor-workbench regressions passed.

- Normal status questions no longer wait for the optional SAGA deterministic
  HAZOP endpoint. The local snapshot answers routine status immediately.
- Remote HAZOP cross-checks remain enabled for active/retained faults, releases,
  relief-valve openings, non-normal analysis states and explicit alarm,
  threshold, leak, fire or isolation questions.
- Emergency impact calculation and the separate one-pass LLM assistant route
  are unchanged, so this optimization does not suppress consequence analysis.

Verification:

- Direct-QA, SAGA-chat and sensor-workbench suites: 50 passed.

## 2026-10-10 - Recheck public actual-hydrogen spatial evidence without promoting a weak prior

Status: implemented; public intake, diagnostic and grounding regressions passed.

- Re-audited the local Figshare release used for the open-channel hydrogen
  experiments. The intake remains 23 manifest files with 22 locally available
  experiment archives, each retained by hash and schema summary; no raw rows
  are added to the assistant evidence envelope.
- Re-ran the post-access spatial diagnostic on all 22 experiments and 638
  sensor-case observations. A geometry-only distance/downward ranking is not
  transferable (median response-rank Spearman rho 0.0318; top-quartile recall
  0.3864), so the runtime detector routing and risk-distance model were not
  changed.
- The bounded actual-hydrogen placement evidence remains descriptive: the
  higher sensor layer and near-source lower sensors provide a rationale for
  layered coverage in confined spaces, but it is not an outdoor HRS map,
  independent spatial validation, or full-loop station validation.

Verification:

- Targeted Figshare, USN spatial, grounding, validation API and readiness
  suites: 36 passed.
- IJHE readiness audit remains 127 PASS / 10 FAIL / 7 PENDING;
  `bounded_ijhe_submission_ready=false` and `full_user_objective_ready=false`.
## 2026-10-10 - Fast-lane scientific-screen separation

Status: implemented; P0 execution is now parallel and reports process health
separately from the scientific screening outcome.

- `scripts/run_priority_diagnostics.py` now parses each child diagnostic's
  machine-readable summary. A zero exit code means the diagnostic completed;
  it no longer implies that the model passed its declared screen.
- `scripts/run_priority_focus.py --priority P0` completed in 3.6 s. The two
  software tracks passed, the MC SOC/EOS boundary screen passed 8/8, and the
  measured-boundary vehicle-tank replay is explicitly reported as
  `scientific_screen_status=FAIL` with 0/8 joint passes.
- This keeps the negative MC result visible instead of allowing a fast process
  check to look like model validation. It does not change runtime parameters,
  the frozen protocol, or the readiness gate.

Verification:

- `tests/test_priority_diagnostics.py tests/test_priority_focus.py`: 4 passed.
- P0 fast lane: process PASS, scientific screen FAIL only for
  `mc_tank_boundary`; duration 3.6 s.

## 2026-10-10 - P1 component lane rechecked in parallel

Status: no new P1 regression; the development-only Dickens mixed-convection
screen remains 3/3, while H2SAFE and Schefer remain process-only diagnostics.

- `scripts/run_priority_focus.py --priority P1 --max-workers 4` completed in
  11.5 s.
- The virtual-safety software suite passed 23 tests. The mixed-convection
  diagnostic reported 3/3 joint screens, but its claim boundary remains
  development-only and no runtime parameter was changed.
- The remaining material scientific blocker is therefore still the P0 MC
  vehicle-tank replay and the missing synchronized receiving-vessel/controller
  full-loop cohort; sequential broad regression would not remove either one.

## 2026-10-10 - Ground the retained MC tank negative result in the LLM envelope

Status: implemented; the main evidence API and prompt summary now carry the
aggregate MC vehicle-tank result without exposing raw rows.

- Added `public_mc_tank_boundary_diagnostic` to the privacy-bounded evidence
  inventory: 8 cases, 0 joint screening passes, mean pressure RMSE 4.376 MPa,
  temperature RMSE 9.052 °C and SOC RMSE 5.584 percentage points.
- The record is explicitly marked post-outcome, diagnostic-only,
  runtime-unchanged, full-loop-ineligible and promotion-prohibited.
- This closes a grounding gap: the LLM now receives the negative P0 result
  itself, alongside the already-grounded geometry and source-boundary
  sensitivities, so it cannot describe the MC replay as a validation pass.

Verification:

- Validation evidence, local evidence and LLM grounding suites: 36 passed.

## 2026-10-10 - Switch development to impact-first execution

Status: implemented; the active queue is now ordered by objective impact rather
than by document or directory order.

- P0 is reserved for evidence that can change the full-station readiness
  decision: synchronized receiving-vessel/controller validation, consequence
  boundary validation, and any failed scientific screen that could be closed
  with already available data.
- P1 covers independent component and spatial checks that can run in parallel
  while P0 data are unavailable. P2 covers manuscript, UI, and presentation
  work and is not allowed to delay P0/P1 execution.
- The fast lane remains process-parallel: `run_priority_focus.py --priority
  P0` completes in about 3--4 s on the current workspace. A completed child
  process is still reported separately from its scientific screen, so speed
  cannot hide a negative result.
- The largest unresolved gate is `full_loop_external_validation`. The local
  public files do not contain eight eligible synchronized vehicle pressure,
  temperature, mass-flow, protocol/controller, and geometry traces. The
  existing metadata-only intake contract is ready to quarantine and hash such
  a bundle as soon as a rights-cleared custodian provides it; no raw private
  rows or site identity are required in the repository.

Current decision snapshot remains **127 PASS / 10 FAIL / 7 PENDING**;
`bounded_ijhe_submission_ready=false` and
`full_user_objective_ready=false`. The queue therefore continues with the
highest-impact available diagnostic instead of waiting for sequential cleanup.

Verification:

- P0 priority focus: process PASS, scientific screen BLOCKED only for
  `mc_tank_boundary`, approximately 3.4 s.
- Priority and readiness regression suites: 10 passed.
