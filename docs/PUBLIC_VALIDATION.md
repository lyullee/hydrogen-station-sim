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
| HIAD 2.2, European Commission JRC | Independent real-incident decision cases | 34 HRS events; 33 with at least one response/lesson/corrective field | Development/holdout casebook and blinded expert review |
| USN/FFI open-channel dispersion data | Consequence/detector benchmark | 22 releases, 29 concentration sensors, 0.029–1.250 g/s | Spatial/temporal hydrogen-concentration model validation after geometry mapping |

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
  h2protocol_j2601_tables hiad_2_2 hydrogen_dispersion_channel
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
unfitted tank overheated and the dispenser under-delivered mass. After the tank
fit is frozen, select a single dispenser flow-area multiplier only on the eight
development fills declared in `research/analysis_plan.json`:

```powershell
.venv\Scripts\python.exe scripts\calibrate_closed_loop_flow.py --jobs 6
```

H2P-L06 was used during exploratory diagnosis and is permanently excluded from
the declared comparison set. Once the calibration file exists, run the eleven
declared cases:

```powershell
.venv\Scripts\python.exe scripts\run_h2protocol_validation.py `
  --tank-validation-json data\public_validation\results\tank_model\validation.json `
  --flow-calibration-json data\public_validation\results\closed_loop_flow_calibration\calibration.json `
  --lab-test-numbers 3,9,12,15,18,21,24,27,30,33,36 `
  --output data\public_validation\results\closed_loop_confirmation_after_antiwindup `
  --jobs 6
```

The first comparison was inspected before structural controller and cascade
corrections, so all subsequent runs on these cases are internal iteration evidence,
not a pristine untouched external holdout. The frozen global flow-area multiplier
remains 1.25. A clean run from commit `55206694bc70d61ccc7521fad563ea15e466f302`
corrected flow-limit anti-windup, a false fixed-temperature precooler trip, and
per-dispenser cascade progression without refitting any parameter. Mean pressure,
temperature and SOC RMSE improved from 11.842 MPa, 10.292 °C and 15.347 percentage
points to 7.213 MPa, 9.179 °C and 10.112 percentage points. All 11 cases still
failed at least one predeclared engineering screen. The eight development cases
also passed 0/8 screens, with mean RMSE of 13.695 MPa, 21.634 °C and 17.668
percentage points. Do not tune further against the 11 comparison cases. Report
the result as a negative closed-loop validation finding and keep the stronger
measured-boundary tank validation claim separate.

The machine-readable clean-run evidence is committed as
`research/closed_loop_development_structural_fix.json`,
`research/closed_loop_development_structural_fix.csv`,
`research/closed_loop_internal_confirmation_structural_fix.json`, and
`research/closed_loop_internal_confirmation_structural_fix.csv`.

Every generated JSON and Markdown report records the source commit and whether
the worktree was dirty. Publication results must be regenerated from a clean,
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

## Publication-readiness gate

Treat an IJHE-level submission as ready only when all of the following evidence
exists and the results support the stated claims:

1. **Process physics:** all 36 external fills run from a frozen model commit;
   errors, confidence intervals, environmental strata, capacity strata and
   residual plots are reported. Calibration and validation cases are separated
   if any parameter fitting is introduced.
2. **Release/consequence physics:** the production consequence path is validated
   against an applicable public experiment or the exact HyRAM+ validation basis
   is documented. The open-channel data cannot validate an outdoor station model
   until release and sensor geometry are mapped explicitly.
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
