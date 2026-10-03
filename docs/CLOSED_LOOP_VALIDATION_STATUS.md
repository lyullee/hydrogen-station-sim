# Closed-loop validation status

## Decision

The measured-boundary Type-IV tank model has useful external agreement, but the
full controller–cascade–precooler–vehicle loop is not yet validated for a broad
IJHE claim. The current evidence must be reported as a mixed result rather than a
successful full-station validation.

## Frozen evidence

All results below were generated from clean commit
`55206694bc70d61ccc7521fad563ea15e466f302` with the two global tank parameters
and the 1.25 dispenser flow-area multiplier already frozen. The structural fix
changed no fitted parameter.

| Evaluation set | Cases | Cases passing all project screens | Mean pressure RMSE | Mean temperature RMSE | Mean SOC RMSE |
|---|---:|---:|---:|---:|---:|
| Development fills | 8 | 0 | 13.695 MPa | 21.634 °C | 17.668 %p |
| Already-inspected internal comparison fills | 11 | 0 | 7.213 MPa | 9.179 °C | 10.112 %p |
| Frozen measured-boundary tank validation | 12 | not evaluated by the closed-loop screen | 3.905 MPa | 4.694 °C | 3.812 %p |

The project screens require pressure RMSE no greater than 5 MPa, temperature RMSE
no greater than 10 °C, and absolute final SOC error no greater than 5 percentage
points. They are project criteria, not SAE acceptance limits.

## What the structural correction fixed

- A flow-limited controller command could back-calculate a large negative
  integral and close the PCV while pressure error remained positive.
- A fixed −20 °C precooler trip incorrectly stopped slower or warmer temperature
  classes; the trip now follows the requested delivery-temperature class while
  preserving the default T40 threshold.
- Cascade selection can no longer fall back to a lower bank during the same fill,
  and the two dispenser circuits keep independent dispatch state.
- The upstream cascade valve scales PCV supply while hose line-pack remains able
  to discharge through the nozzle during break-before-make switching.
- Offline validation skips interactive idle pacing without changing simulated
  timestamps or states.

## Interpretation and next evidence

The comparison-set improvement is real but cannot restore holdout status because
those cases had already been inspected. Remaining discrepancies are concentrated
in the closed-loop schedule and dispenser boundary representation. Public files
provide APRR and measured traces but not the complete proprietary J2601 lookup
table or every station command transition. A defensible next study must freeze a
new protocol representation before collecting a new external set, or limit the
physics claim to the measured-boundary tank model and present the full loop as a
demonstrator with negative validation evidence.

IJHE readiness also still requires the preregistered blinded HIAD/SAGA review by
at least two qualified independent reviewers. Software tests and LLM self-scoring
cannot substitute for that assessment.
