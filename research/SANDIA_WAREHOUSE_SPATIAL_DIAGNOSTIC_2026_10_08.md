# Sandia warehouse actual-hydrogen spatial-rank diagnostic

The H2SAFE-derived orientation-class candidate was frozen in commit `2056c04` before these six public numerical outcomes were inspected. The diagnostic itself was formalised after outcome access, so this is external post-access evidence and not independent validation.

| Metric | Original buoyant rank | Orientation-class candidate |
|---|---:|---:|
| Spearman rho | 0.600 | 0.943 |
| Kendall tau-b | 0.467 | 0.867 |
| Top-3 recall | 0.667 | 1.000 |
| Highest-ranked sensor correct | False | True |

Observed descending order: `S01, S06, S07, S04, S11, S08`.
Candidate descending order: `S01, S06, S07, S04, S08, S11`.

The candidate improves Spearman rho from 0.600 to 0.943 without fitting. It correctly identifies S01 and the three highest-response sensors. The bottom two sensors are reversed. Runtime routing remains disabled and the H2SAFE gate remains failed.

Source: [Gexcon Sandia validation case](https://knowledge.gexcon.com/docs/sandia-validation-case), based on [Ekoto et al. (2012)](https://doi.org/10.1016/j.ijhydene.2012.03.161).

## Claim boundary

This single six-point combined-test summary is actual-hydrogen external diagnostic evidence for spatial ordering only. It is not a prospective validation, detector calibration, concentration prediction, alarm-setpoint, outdoor HRS placement, CFD, consequence-distance, ESD or full-loop claim.
