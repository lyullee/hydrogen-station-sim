# Public-data validation protocol

## Objective and claim boundary

The study objective is a hydrogen-refuelling-station safety digital twin whose
process predictions are tested against public experiments and whose SAGA-PY
decision support is tested on independent incident evidence. A green software
test suite proves implementation consistency; it does not prove physical
accuracy, emergency-response correctness, field safety, or regulatory approval.

The repository commits source metadata, checksums, parsers, metrics, and study
scripts. Raw third-party files and generated model answers remain under the
gitignored `data/` directory. This preserves licensing boundaries and prevents a
paper result from silently becoming part of the source tree.

## Evidence sets

| Evidence | Role | Current normalized scope | Use in the study |
|---|---|---:|---|
| Powertech Labs SAE J2601 Tables Method data | External process-physics validation | 36 fills; 2.0, 4.7, 5.9 and 9.8 kg nominal tanks | Pressure, tank-gas temperature and SOC traces on the experimental clock |
| Powertech Labs SAE J2601 MC Default bench data | Prospectively frozen external closed-loop holdout | 8 fills; six 4.7 kg cases plus 2.0 and 9.8 kg tanks | Frozen controller, precooling and tank-response transportability |
| HIAD 2.2, European Commission JRC | Independent real-incident decision cases | 34 HRS events; 33 with at least one response/lesson/corrective field | Development/holdout casebook and blinded expert review |
| USN/FFI open-channel dispersion data | Bounded consequence/detector-logic benchmark | 22 releases, 29 concentration sensors, 0.029–1.250 g/s | Measured concentration replay through declared alarm/trip thresholds; not an outdoor HRS full-loop holdout |

Exact URLs, attribution, rights notes and immutable file digests are in
`research/data_sources.json`. The acquisition log records the files actually
verified on the local machine.
The frozen endpoints, data split, uncertainty method, and claim rules are in
`research/analysis_plan.json`; its status is retrospective rather than a claimed
prospective registration.

## Reproduce acquisition and normalization

Install the research and test dependencies, fetch the sources, and prepare them:

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -m pip install -e ".[research,test]"
.venv\Scripts\python.exe scripts\fetch_public_validation_data.py `
  h2protocol_j2601_tables h2protocol_mc_default hiad_2_2 hydrogen_dispersion_channel
.venv\Scripts\python.exe scripts\prepare_public_validation_data.py
```

Normalization must report 36 J2601 fills, 34 core HRS incidents and 22
dispersion tests. It handles documented source-workbook variants, detects the
duplicate copy of J2601 test workbook 18, and refuses conflicting duplicates.
One flow-meter validation workbook has no recorded SOC; its SOC is explicitly
marked as derived from measured pressure and tank temperature using the same
density definition as the controller.

To update only one already downloaded data product:

```powershell
.venv\Scripts\python.exe scripts\prepare_public_validation_data.py --datasets dispersion
```

To reproduce the bounded detector-logic evidence record (1.0 vol% alarm,
2.0 vol% trip and 0.5 s persistence):

```powershell
.venv\Scripts\python.exe scripts\run_dispersion_detector_validation.py `
  --output research/dispersion_detector_logic_validation.json
```

The replay checks deterministic threshold, persistence and sampling-gap
handling against all 22 public experiments. It does not validate detector
response dynamics, placement, ESD effectiveness, outdoor station dispersion or
the complete refuelling process model. See
[`DISPERSION_DETECTOR_LOGIC_VALIDATION.md`](../research/DISPERSION_DETECTOR_LOGIC_VALIDATION.md)
for the exact claim boundary and archive digests.

To normalize only the MC Default holdout:

```powershell
.venv\Scripts\python.exe scripts\prepare_public_validation_data.py --datasets mc_default
```

## J2601 baseline validation

Run every external fill without fitting case-specific model parameters:

```powershell
.venv\Scripts\python.exe scripts\run_h2protocol_validation.py --jobs 4
```

Each experiment supplies initial pressure and gas temperature, chamber
temperature, scheduled APRR, median inlet-gas temperature, final comparison time
and nominal tank capacity. Maximum mass flow remains fixed at 60 g/s. Prediction
is interpolated onto the experimental timestamps without dynamic time warping.

The public overview does not contain machine-readable internal vessel volumes.
The baseline therefore scales volume from the demonstrator reference of
0.122 m³ per 4.7 kg, thermal mass with volume, and heat-transfer conductance with
surface area. Every output row records this assumption. Exact vessel geometry
should replace it before the final submission if it can be obtained from the
associated SAE report or authors.

The report includes per-case pressure, temperature and SOC RMSE/MAE, final and
peak errors, grouped data needed for environmental/capacity analysis, and a
10,000-resample bootstrap 95% confidence interval of the mean. The included
screening limits are predeclared project criteria rather than SAE acceptance
rules. A failed screen is a model-development result and must not be removed or
relabelled.

The closed-loop result combines the controller, dispenser hydraulics,
pre-cooling and tank. To isolate the vehicle tank, run a second, predeclared
calibration/validation experiment with measured flow and inlet temperature as
boundary conditions:

```powershell
.venv\Scripts\python.exe scripts\run_tank_model_validation.py
.venv\Scripts\python.exe scripts\plot_tank_validation.py
```

The frozen validation set is every third laboratory test (3, 6, …, 36), giving
12 held-out fills across the experiment sequence. The remaining eligible fills estimate
only two global parameters: effective-volume and gas-to-liner heat-transfer
multipliers. Case-specific fitting is prohibited. The resulting tank validation
does not validate the closed-loop controller or dispenser. Publication figures
are written in both vector PDF and 300 dpi PNG form.

Before fitting, an experiment-only mass-closure screen compares integrated
measured flow with the nominal capacity change implied by reported SOC. The
predeclared admissible ratio is 0.8–1.2. Excluded cases and ratios remain in the
report; this screen never uses a model prediction. It currently identifies the
repeat-fuelling trial whose measured flow implies substantially more inventory
than its nominal SOC change.

The original closed-loop baseline failed its engineering screen because the
unfitted tank overheated and the dispenser under-delivered mass. Mass-flow timing
diagnostics then exposed a preprocessing error in H2P-L29: an isolated 1.526 g/s
pulse at workbook time zero pulled the old normalized start 369.5 s ahead of the
sustained fill. The corrected parser clusters above-threshold samples, removes
negligible leading/trailing clusters by integrated mass, and preserves meaningful
multi-segment fills. The correction, hashes and downstream effect are recorded in
`research/h2protocol_active_fill_correction.json`. H2P-L29 now contains 399 samples
over 199 s instead of 1,143 samples over 571 s.

The tank model was refitted after this correction. Its global effective-volume
and gas-to-liner-UA multipliers are 1.052729 and 31.460657. The 12 frozen
measured-boundary validation fills have mean pressure, temperature and SOC RMSE
of 3.841 MPa, 4.833 °C and 3.850 percentage points. After freezing that fit,
select a single dispenser flow-area multiplier only on the eight development
fills declared in `research/analysis_plan.json`:

```powershell
.venv\Scripts\python.exe scripts\calibrate_closed_loop_flow.py --jobs 6
```

H2P-L06 was used during exploratory diagnosis and is permanently excluded from
the declared comparison set. The initial candidate grid ended at its best value,
so the development-only search was extended to 2.5 before evaluating the eleven
comparison fills. It selected a flow-area multiplier of 2.0. Density-based SOC
also now uses each experiment's nominal working pressure; this corrects the 35 MPa
H2P-L19 experiment without changing the default 70 MPa station configuration.
Once the calibration file exists, run the eleven declared cases:

```powershell
.venv\Scripts\python.exe scripts\run_h2protocol_validation.py `
  --tank-validation-json data\public_validation\results\tank_model\validation.json `
  --flow-calibration-json data\public_validation\results\closed_loop_flow_calibration\calibration.json `
  --lab-test-numbers 3,9,12,15,18,21,24,27,30,33,36 `
  --thermal-calibration-json data\public_validation\results\closed_loop_thermal_calibration_v2\calibration.json `
  --output data\public_validation\results\closed_loop_internal_comparison_v2 `
  --jobs 6
```

The first comparison was inspected before structural controller and cascade
corrections, so every later run on these cases is internal iteration evidence,
not a pristine untouched external holdout. The corrected v2 pipeline uses the
refitted tank, flow-area multiplier 2.0 and effective precooler-duty multiplier
16. The latter was selected from a protocol frozen before evaluation; it again
fell at the candidate upper bound, while improvement from 8 to 16 was small.
Larger values were not searched because the remaining error is not defensibly
identifiable as cooling duty alone.

With this final development configuration, 1/8 development fills passed all
screens (mean RMSE 6.602 MPa, 11.428 °C and 7.297 percentage points). The already-
inspected internal comparison passed 2/11 (4.530 MPa, 7.819 °C and 4.625
percentage points). This is a material improvement but still a negative full-loop
result. Do not tune against the 11 comparison cases. Keep the measured-boundary
tank claim separate from controller, cascade, dispenser and precooler claims.

### Prospectively frozen MC Default external holdout

The separate MC Default archive was acquired from the same publisher only after
the exact archive SHA-256, eight eligible workbook paths, frozen model commit,
global tank and dispenser parameters, exclusion rules, schedule mapping and
engineering screens were committed in
`research/mc_default_external_holdout_protocol.json`. The selected workbook
outcomes were unopened at protocol freeze. Reproduce the evaluation with:

```powershell
.venv\Scripts\python.exe scripts\fetch_public_validation_data.py h2protocol_mc_default
.venv\Scripts\python.exe scripts\prepare_public_validation_data.py --datasets mc_default
.venv\Scripts\python.exe scripts\run_mc_default_holdout.py --jobs 4
```

The frozen implementation accepts one constant APRR, so each published MC
pressure--time schedule is represented by its endpoint-equivalent average ramp.
This is an explicit model approximation, not an implementation or certification
of the proprietary MC Formula. No case-specific fitting, post-freeze parameter
tuning, dynamic time warping or failed-case exclusion was allowed.

The prospective result was **0/8 joint engineering-screen passes**. Aggregate
mean RMSE was 15.862 MPa for pressure, 13.230 °C for tank temperature and 18.082
percentage points for SOC. Five cases stopped on the model's temperature safety
logic, and all eight final SOC errors were negative. The machine-readable result,
case table and report are committed under
`data/public_validation/results/closed_loop_external_holdout/`. These eight cases
are now consumed external evaluation evidence and must not be used to tune the
next model. The bench data do not expose every internal three-bank valve command,
so even a passing result would not alone validate every cascade dispatch state.

The machine-readable clean-run evidence is committed as
`research/closed_loop_development_structural_fix.json`,
`research/closed_loop_development_structural_fix.csv`,
`research/closed_loop_internal_confirmation_structural_fix.json`, and
`research/closed_loop_internal_confirmation_structural_fix.csv`.

The first thermal calibration in
`research/closed_loop_thermal_calibration_protocol.json` is retained as historical
development evidence and is superseded by the corrected parser/tank/SOC pipeline.
The replacement protocol is
`research/closed_loop_thermal_calibration_protocol_v2.json`; its machine-readable
candidate, development and internal-comparison results are committed under
`research/*_v2.json` and `research/*_v2.csv`. Neither calibration was rerun against
the consumed MC Default outcomes. The external 0/8 result remains an honest
historical failure of its frozen pre-correction model and cannot validate the
corrected model.

Each final comparison JSON and Markdown report records the source commit and
whether the worktree was dirty; calibration reports link to their frozen model
commit and protocol. Publication results must be regenerated from a clean,
immutable release commit; a commit hash alone does not identify uncommitted model
code.

## HIAD decision-support evaluation

First generate a development or untouched holdout casebook:

```powershell
.venv\Scripts\python.exe scripts\run_hiad_decision_evaluation.py `
  --split development `
  --prepare-casebook
```

A qualified coordinator must remove or rewrite narrative text that reveals the
recorded response, set `narrative_action_leakage_review` to `PASS`, set
`expert_vignette_approved` to `YES`, and freeze the approved file. Then start
SAGA-PY at its isolated integration endpoint and collect responses:

```powershell
.venv\Scripts\python.exe scripts\run_hiad_decision_evaluation.py `
  --saga-url http://127.0.0.1:8090 `
  --provider groq `
  --split development `
  --approved-casebook approved_development_casebook.json `
  --repeats 3 `
  --include-standards-rag
```

Only the historical observation is sent to SAGA. HIAD emergency actions,
lessons, corrective measures and references are withheld in the coordinator's
casebook. Because incident narratives can themselves contain hindsight actions,
every vignette is initially labelled `narrative_action_leakage_review=PENDING`
and `expert_vignette_approved=NO`. A reported holdout experiment may use only
vignettes manually reviewed and frozen before model collection.

This collection produces alarm-only, direct one-pass LLM, and standards-document
RAG variants. It isolates the added value of language generation and retrieval;
it does not claim that the HIAD narrative contains live process or consequence
measurements. The generated `blind_expert_review.csv` hides the response variant.
`reviewer_case_reference.csv` supplies the observation and withheld HIAD response
fields without revealing the allocation. Three
independent hydrogen-safety reviewers should score situation accuracy, immediate
action correctness, priority order, stabilization/restart criteria, prevention,
evidence grounding and operator usability. Critical omissions and unsafe advice
are separate binary endpoints. The allocation key must remain with the study
coordinator until ratings are locked.

After three reviewers return separate completed copies and the coordinator
marks approved casebook vignettes `YES`, analyze the locked files:

```powershell
.venv\Scripts\python.exe scripts\analyze_hiad_expert_review.py `
  --allocation data\public_validation\results\hiad_decision\allocation_key.csv `
  --casebook data\public_validation\results\hiad_decision\casebook_snapshot.json `
  --ratings reviewer_1.csv reviewer_2.csv reviewer_3.csv `
  --reviewer-qualifications reviewer_qualifications.csv
```

The analyzer reports each model variant's paired event-level difference versus
alarm-only with a bootstrap confidence interval and Wilcoxon test, critical-
omission and unsafe-advice rates, and pairwise quadratic-weighted kappa for each
ordinal criterion.
The complete reviewer qualifications, masking, rubric, and locking procedure are
specified in `docs/EXPERT_REVIEW_PROTOCOL.md`.

The final analysis should report paired system differences with confidence
intervals and an appropriate paired test, plus inter-rater agreement for each
ordinal criterion. Model, provider, prompt, temperature, token limit, latency,
failures, source commits and every repeat must be retained. Do not substitute an
LLM-as-judge score for the primary expert assessment.

## Consequence-model boundary and adapter verification

The production HyRAM adapter now evaluates three distinct quantities for each
release: the 4 vol% unignited-jet plume centerline distance, sampled 5 kW/m² jet
fire radiation, and sampled 5 kPa explosion overpressure. These are reported as
different fields. The plume distance is directional and must not be rendered or
described as a spherical exclusion radius. The heat/overpressure distance remains
the farthest configured observation point exceeding either threshold, with the
next sampled point reported when available.

For choked releases HyRAM may reject a supplied process mass-flow override and
calculate flow from source pressure, temperature, orifice and discharge
coefficient. Reports therefore retain both
`requested_mass_flow_override_kg_s` and
`modeled_consequence_mass_flow_kg_s`; the latter is the value that generated the
plume and flame fields. Treating the requested value as the modeled value would
make the process/consequence coupling appear more exact than it is.

The USN/FFI dataset and article define a downward 4.6 mm release inside a
5.8 m × 0.9 m × 0.8 m open-ended channel with 29 fixed sensors. This is valuable
for a confined-channel dispersion or CFD benchmark, but it is not geometrically
applicable to the current free-jet station adapter. It must not be used to claim
validation of the outdoor station plume. The underlying HyRAM physics validation
basis is the Sandia report recorded in `research/data_sources.json`; a final
manuscript must additionally verify this repository's adapter inputs and outputs
against the installed HyRAM version and disclose the version gap between the
published validation report and HyRAM 6.1.

The adapter verification is reproducible from the exact upstream `v6.1` tag:

```powershell
git clone --depth 1 --branch v6.1 `
  https://github.com/sandialabs/hyram.git `
  data\public_validation\raw\hyram-v6.1
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe scripts\run_hyram_adapter_verification.py
```

The script hashes every installed HyRAM Python source file and compares it with
the upstream tag. It runs Sandia's plume, heat-flux and unconfined-overpressure
validation modules, followed by station-scale parity cases that call the
production adapter and public HyRAM API independently. The report keeps the SI
unit mapping and per-field numerical errors. Passing this check establishes
adapter fidelity to the installed package; it does not turn a sampled effect
distance into a regulatory separation distance or independently validate the
station geometry.

The clean-commit result is archived in
[`HYRAM_ADAPTER_VERIFICATION.md`](HYRAM_ADAPTER_VERIFICATION.md), with complete
machine-readable values and per-field errors in
[`research/hyram_adapter_verification.json`](../research/hyram_adapter_verification.json).

The remaining display transformation is frozen and checked with:

```powershell
$env:PYTHONPATH = "src;."
.venv\Scripts\python.exe scripts\validate_consequence_geometry.py
```

This links three geometrically applicable public evidence families to the exact
HyRAM+ source, production adapter and browser contract. The browser keeps the
sampled 5 kW/m² or 5 kPa radial band separate from the directional 4 vol% plume,
retains metres and release angle, and regression-tests the mapping. The report is
[`CONSEQUENCE_GEOMETRY_VALIDATION.md`](../research/CONSEQUENCE_GEOMETRY_VALIDATION.md).
Its pass applies only to outdoor unconfined free-jet screening. It explicitly
excludes site-specific wind, buildings, congestion, terrain, certified safety
boundaries and regulatory separation distances.

## PRESLHY ambient blowdown validation

PRESLHY E3.1 supplies independent high-pressure hydrogen discharge records for
a 2.815 L vessel and 0.5, 1, 2 and 4 mm apertures. The prospective protocol in
`research/preslhy_blowdown_validation_protocol.json` was frozen before any
numerical Excel outcome was opened. It fixes the source/model hashes, data
eligibility, time synchronization, pressure interpretation, error screens,
bootstrap seed and negative-result policy.

The official RADAR TAR is about 1.3 GB and includes photographs and 80 K data.
The acquisition utility reads TAR headers with verified HTTP byte ranges and
downloads only the four `300K_DATA` ZIP members. Its index and partial-download
checkpoints are stored under the gitignored raw-data directory, so an
intermittent repository connection can be resumed without restarting:

```powershell
.venv\Scripts\python.exe scripts\fetch_preslhy_ambient_packages.py
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe scripts\run_preslhy_blowdown_validation.py
.venv\Scripts\python.exe scripts\audit_ijhe_readiness.py
```

If the RADAR endpoint repeatedly drops short index requests, cache the remaining
TAR tail over a resumable long stream and perform the same header verification
and member extraction locally:

```powershell
.venv\Scripts\python.exe scripts\fetch_preslhy_ambient_packages.py --cache-tail
```

The tail cache remains under the gitignored raw-data directory. It is an
acquisition transport fallback only; it does not alter case eligibility,
model inputs, endpoints or decision thresholds.

The primary case screens are pressure NRMSE at most 10% of initial absolute
pressure and time-to-50%-initial-gauge-pressure error at most 20%. At least 12
cases across three nozzle and three pressure groups are required, and at least
70% must pass both screens. An eligible integration failure remains a failed
case. Sensitivity at discharge coefficients 0.7 and 0.9 cannot replace the
frozen primary result at 0.8.

This test can support only the ambient direct-aperture source-depletion claim.
It does not validate the complete fueling loop, cryogenic two-phase release,
site vent-stack hydraulics, pipe backpressure, ignition, dispersion, emergency
separation distance or regulatory safety distance.

The completed frozen evaluation retained all 22 eligible cases and excluded
none. Eleven cases passed both primary screens: 50.0% (case-bootstrap 95% CI
31.8–72.7%), below the predeclared 70% criterion. Six high-pressure cases had
thermophysical-domain failures and were counted as failures. The direct-aperture
source-depletion claim is therefore **not supported** for this model revision.
The case-level and stratified evidence is archived in
[`PRESLHY_BLOWDOWN_EXTERNAL_VALIDATION.md`](../research/PRESLHY_BLOWDOWN_EXTERNAL_VALIDATION.md).
These cases are now consumed development evidence; any revised heat-transfer,
property-domain or valve/line model requires a separately frozen external
holdout.

## Publication-readiness gate

Treat an IJHE-level submission as ready only when all of the following evidence
exists and the results support the stated claims:

1. **Process physics:** all 36 external fills run from a frozen model commit;
   errors, confidence intervals, environmental strata, capacity strata and
   residual plots are reported. Calibration and validation cases are separated
   if any parameter fitting is introduced.
2. **Release/consequence physics:** the frozen PRESLHY ambient blowdown test
   meets its direct-aperture screens, and the production consequence path is
   traceable to the exact HyRAM+ validation basis and adapter-parity evidence.
   These remain separate source-depletion and free-jet consequence claims.
3. **Incident decision support:** the holdout vignettes are checked for response
   leakage; three qualified reviewers complete blinded ratings; agreement,
   unsafe-advice rate, critical-omission rate, response latency and failed-call
   rate are reported.
4. **Ablation:** alarm-only, process context, process plus consequence results,
   and full evidence retrieval are compared under the same cases and response
   budget. This isolates what SAGA contributes.
5. **Reproducibility:** code releases and DOIs identify immutable versions;
   acquisition digests, environment, model/provider versions, random seeds,
   prompts and analysis scripts are archived without API keys or restricted raw
   data.
6. **Claim discipline:** the manuscript distinguishes a validated research
   prototype from a certified filling protocol, safety instrumented system,
   evacuation model or regulatory decision tool.

Until these gates are satisfied, describe the evidence as baseline validation
work in progress. Software features, visual realism and passing unit tests do not
replace these gates.
