# Minimum evaluation package for a digital-twin/SAGA-PY paper

## Purpose

This package turns two existing system boundaries into repeatable measurements:

1. the H70 simulator's externally supplied fueling schedule boundary; and
2. the difference between a compact deterministic alarm and the same snapshot
   interpreted by the isolated SAGA-PY digital-twin assistant.

It is intended for a prototype or case-study paper. It does not establish field
safety, certify a station, or demonstrate full SAE J2601 conformity.

## Run

Install the simulator test/API dependencies and run the offline part:

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe scripts\run_paper_evaluation.py
```

This writes `evaluation.json`, `decision_support.csv`, and `report.md` under
`data/paper_evaluation/`. The `data` directory is deliberately untracked because
real LLM outputs and experiment metadata vary by run.

For the linked experiment, start SAGA-PY on its normal local port with one
manually selected provider, then run:

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe scripts\run_paper_evaluation.py `
  --saga-url http://127.0.0.1:8090 `
  --provider groq `
  --repeats 5 `
  --require-saga
```

`--require-saga` prevents an accidentally disconnected run from being reported
as an LLM experiment. The script never reads or writes provider keys; SAGA-PY
retains that responsibility. Record both repositories' commit hashes, model name,
provider, run time and configuration with the exported files.

## Protocol-boundary metrics

The audit calculates scheduled and observed APRR, pressure-reference RMSE, peak
mass flow, peak gas temperature, final pressure and SOC, stop reason, and margins
to the 87.5 MPa hard pressure boundary, 85 °C gas-temperature stop, and configured
mass-flow limit. A result passes the implemented schedule boundary only when the
fill completes on a configured target, the APRR error is within the declared
tolerance, and none of those safety limits is exceeded.

The public repository does not include proprietary SAE J2601 lookup tables or an
MC Formula implementation. A paper must therefore use wording such as
"SAE J2601-compatible schedule boundary" and report the actual supplied APRR,
temperature and termination settings. Do not use "SAE J2601 certified" or
"protocol compliant" without licensed inputs and the required hardware/test
evidence. Final SOC must be shown separately: reaching a user-selected 70 MPa
pressure target at elevated gas temperature need not equal 100% SOC.

## SAGA linkage A/B metrics

Each fixed case is evaluated twice:

| Variant | Input | Output role |
|---|---|---|
| `alarm-only` | Tag, value and severity | Existing deterministic alert baseline |
| `saga-linked` | The same alert plus calculated impact and approved action context | One-pass SAGA-PY operator explanation |

The transparent rubric measures situation identification, coverage and order of
immediate actions, prevention/recovery coverage, use of calculated impact data,
unsupported numerical claims, response length and latency. It uses explicit
Korean concept alternatives rather than a second LLM judge. Full answer text is
kept in the JSON/CSV output so a reviewer can reproduce every score.

The retained 34-case run also has a post-outcome selectivity audit at
`research/hiad_response_selectivity_audit_2026_10_08.json`. It reuses the saved
answers without provider calls and reports reference-category precision/F1,
non-reference action burden and response length. These metrics expose a key
tradeoff hidden by recall alone: more relevant actions can arrive with more text
and more categories for an operator to process. Because HIAD action fields may be
incomplete, an unreferenced category is additional information, not proof of an
incorrect or unsafe recommendation.

The total score uses situation 25%, action coverage 35%, action order 10%,
prevention 15%, and impact-result use 15%. A non-applicable empty category is
counted as satisfied. Each numerical value with a unit that is absent from the
supplied evidence subtracts 5 points, up to 20 points. Freeze the cases, concept
alternatives, and weights before collecting the reported answers; changing the
rubric after reading an answer introduces evaluator bias.

The bundled two cases are a storage-bank hydrogen leak and vehicle-tank
overtemperature. For a submission, add at least overpressure/relief opening,
external fire, cooling failure and detector failure. Run each model/case at least
five times and report mean, standard deviation and worst result. Have three
gas-safety reviewers independently rate action correctness; report their rubric
and agreement rather than treating keyword coverage as expert validation.

## Minimum claims supported

With the generated evidence, a paper may describe a reproducible prototype that:

- couples process dynamics, alarms, consequence results and a one-pass assistant;
- audits its public fueling-schedule boundary with explicit numerical margins;
- compares alarm-only and LLM-linked decision support under identical snapshots;
- records latency, grounded numerical use and action coverage.

Claims about real-station prediction accuracy require independent measurements or
an accepted reference dataset. Claims about emergency-response correctness require
expert review. Keep calibration cases separate from validation cases.
