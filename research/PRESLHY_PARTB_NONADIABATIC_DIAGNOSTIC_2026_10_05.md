# PRESLHY Part-B non-adiabatic diagnostic (2026-10-05)

The revised non-adiabatic release model was replayed on the five Part-B
ambient cases already used by the frozen holdout. The run uses the reported
0.225 m³ source volume, the model's existing DisCha wall/geometry defaults and
the frozen discharge coefficient of 0.8. Because the Part-B archive does not
publish a complete wall geometry and thermal inventory, this is a sensitivity
diagnostic rather than a Part-B parameterization.

| Case group | Pressure NRMSE | Half-time error | Joint pass |
|---|---:|---:|---:|
| 2 mm, 5 bar | 6.50% | 25.28% | no |
| 2 mm, 3.2 bar | 7.46% | 25.30% | no |
| 4 mm, 5 bar | 7.39% | 15.32% | yes |
| 4 mm, 3.2 bar | 8.55% | 15.26% | yes |
| 4 mm, 4.8 bar | 7.31% | 14.35% | yes |

The joint result remains **3/5 (60%)**, identical to the frozen Part-B result.
Pressure error improves, but both 2 mm cases retain a diameter-dependent
approximately 25% timing error. This indicates that adding the consumed
DisCha wall-thermal sensitivity does not resolve the remaining release-rate
discrepancy; nozzle/manifold geometry or discharge-regime representation must
be measured before a new holdout is designed.

The cases were already outcome-visible, so this record cannot be promoted to
external validation or used to fit a discharge coefficient. The frozen Part-B
result remains authoritative.
