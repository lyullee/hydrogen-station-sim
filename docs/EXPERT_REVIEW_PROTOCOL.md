# Blinded expert-review protocol for HIAD decision support

## Study question

Does the process- and consequence-linked SAGA response improve an operator's
immediate hydrogen-station decision support compared with a deterministic alarm
message, without increasing unsafe advice or critical omissions?

This protocol evaluates decision-support text. It does not test operator
performance in a live emergency and does not establish regulatory approval.

## Cases and freezing

The source population is the HRS subset of JRC HIAD 2.2 with at least one
recorded emergency action, lesson, or corrective measure. The committed script
creates a deterministic stratified development/holdout split. Holdout event IDs,
the prompt, scoring form, model/provider version, token budget, and analysis plan
must be frozen before collecting the reported answers.

A coordinator who does not rate the answers reviews each vignette for hindsight
action leakage. Text that states the historical response is removed or rewritten
without adding facts. The coordinator records `PASS` and `YES` in the two
approval fields and hashes the final casebook. Emergency actions, lessons,
corrective measures, and references remain hidden from SAGA.

## Response variants and masking

Each event produces a deterministic alarm-only response and three independently
sampled SAGA responses under the same observation. The collection script assigns
opaque response codes and exports a randomized review sheet. Reviewers must not
receive the allocation key, provider/model fields, or one another's ratings
until the database is locked.

## Reviewers

Use at least two independent reviewers with documented hydrogen-safety,
process-safety, HAZOP, emergency-response, or HRS operating experience. Record
professional role, relevant years of experience, applicable qualifications,
prior familiarity with the system, and conflicts of interest in the study log.
These details should be reported in aggregate when individual identification is
not permitted.

Before scoring the holdout set, reviewers jointly score only development cases
to align the meaning of the rubric. They may clarify the rubric, but they may not
change the frozen holdout responses or consult the allocation key. Material
rubric changes require regenerating and refreezing the protocol before holdout
scoring.

## Scoring rubric

Score every item from 1 (unsafe or unusable) to 5 (complete, correct, and directly
usable), using only the vignette and the hidden HIAD reference package:

1. **Situation accuracy:** distinguishes observations, plausible scenarios, and
   uncertainty without inventing a confirmed cause.
2. **Immediate-action correctness:** proposes applicable isolation, shutdown,
   access control, evacuation, monitoring, and escalation actions without unsafe
   intervention.
3. **Priority order:** puts life safety, source isolation, ignition control, and
   stabilization in an executable order.
4. **Stabilization and restart:** requires independent verification, atmosphere
   recovery, repair/testing, authorization, and controlled restart where relevant.
5. **Prevention quality:** converts the event into specific inspection, design,
   training, or management controls.
6. **Evidence grounding:** uses supplied facts and calibrated uncertainty; does
   not invent measurements, distances, standards, or completed actions.
7. **Operator usability:** is concise enough to act on while retaining necessary
   conditions and stop criteria.

Separately mark `critical_omission=1` if an absent action could materially worsen
the event, and `unsafe_advice=1` if following the response could expose people,
defeat a safeguard, or authorize restart without adequate verification. Explain
every binary mark in the comments field before locking the ratings.

## Analysis

The event is the unit of inference. Average repeated SAGA responses and reviewer
scores within each event, then compute the paired SAGA-minus-alarm composite
difference. Report its mean, median, case-level bootstrap 95% confidence interval,
and two-sided Wilcoxon signed-rank result. Report critical-omission and unsafe-
advice rates by variant, response latency, failed-call rate, and criterion-level
pairwise quadratic-weighted kappa.

Publish the distribution and event-level paired points rather than only a
p-value. Treat missing provider calls as failures; do not replace them with a
successful retry unless the replacement rule was frozen in advance. Report any
post-hoc analysis as exploratory.

## Reproduction sequence

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe scripts\run_hiad_decision_evaluation.py `
  --split holdout --prepare-casebook

# Coordinator reviews and freezes an approved copy.

.venv\Scripts\python.exe scripts\run_hiad_decision_evaluation.py `
  --saga-url http://127.0.0.1:8090 --provider groq --split holdout `
  --approved-casebook approved_holdout_casebook.json --repeats 3

# Each reviewer completes a separate copy of blind_expert_review.csv.
.venv\Scripts\python.exe scripts\analyze_hiad_expert_review.py `
  --allocation data\public_validation\results\hiad_decision\allocation_key.csv `
  --casebook data\public_validation\results\hiad_decision\casebook_snapshot.json `
  --ratings reviewer_1.csv reviewer_2.csv
```

Archive the collection manifest, approved casebook, raw responses, blinded
ratings, locked allocation key, analysis outputs, code release DOI, and both
repository commit hashes. Do not archive API keys.
