# Closed-loop validation status

## Decision

The measured-boundary Type-IV tank model has useful external agreement, but the
full controller–cascade–precooler–vehicle loop is not validated for a broad IJHE
claim. The corrected development pipeline improves the internal comparison but
does not meet the case-level joint screen often enough. The evidence remains a
mixed, negative full-loop result.

## Corrected evidence

The model files were frozen at
`5977d0be8efb5f57746e7e3cb2e3b9cdb842abcf`. The v2 thermal protocol was added
without changing those files, and final runs were generated from clean commit
`6c22211172d69f9180c6721d1f47e7a40280b69d`.

| Evaluation set | Cases | Cases passing all project screens | Mean pressure RMSE | Mean temperature RMSE | Mean SOC RMSE |
|---|---:|---:|---:|---:|---:|
| Corrected development fills | 8 | 1 | 6.602 MPa | 11.428 °C | 7.297 %p |
| Already-inspected internal comparison fills | 11 | 2 | 4.530 MPa | 7.819 °C | 4.625 %p |
| Frozen measured-boundary tank validation | 12 | not evaluated by the closed-loop screen | 3.841 MPa | 4.833 °C | 3.850 %p |
| Prospectively frozen MC Default holdout, historical frozen model | 8 | 0 | 15.862 MPa | 13.230 °C | 18.082 %p |

The project screens require pressure RMSE no greater than 5 MPa, temperature RMSE
no greater than 10 °C, and absolute final SOC error no greater than 5 percentage
points. They are project criteria, not SAE acceptance limits. The SOC RMSE column
is descriptive; pass/fail uses absolute final SOC error.

## Corrections made after diagnostics

- The active-fill parser now rejects negligible isolated leading/trailing flow
  clusters by integrated mass while preserving meaningful multi-segment fills.
  This removed a 369.5 s false prefill interval from H2P-L29.
- The measured-boundary tank was refitted after normalization. Its global
  effective-volume and gas-to-liner-UA multipliers are 1.052729 and 31.460657.
- Density-based SOC uses the experiment's nominal working pressure, including the
  35 MPa H2P-L19 test, instead of an unconditional 70 MPa reference.
- Development-only flow calibration selected 2.0 from the adaptively extended
  1.0–2.5 range. No internal-comparison or MC Default outcome entered selection.
- The frozen v2 thermal search selected the upper-bound effective-duty multiplier
  16. Improvement above 8 was small; larger values were not searched.
- Earlier controller repairs retained conditional anti-windup, delivery-class-
  aware temperature limits, monotonic cascade progression, per-dispenser state
  and line-pack continuity during bank switching.

## Interpretation and next evidence

The 11 comparison cases were inspected during earlier development and cannot
regain untouched holdout status. The eight MC Default cases were prospectively
frozen for an older model, failed, and are now consumed. They were not rerun after
the parser, nominal-pressure or calibration changes.

Remaining discrepancies are concentrated in case-specific delivery timing,
temperature stops and high-capacity/high-rate conditions such as H2P-L31. The
public files provide APRR and measured traces but not the complete proprietary
J2601 lookup table or every station command transition. A defensible next study
must freeze the corrected model and evaluate a different, untouched external set,
or limit the physics claim to the measured-boundary tank and present the full loop
as a demonstrator with negative validation evidence.

IJHE readiness also requires the preregistered blinded HIAD/SAGA review by three
qualified independent reviewers. Software tests and LLM self-scoring cannot
substitute for that assessment.
