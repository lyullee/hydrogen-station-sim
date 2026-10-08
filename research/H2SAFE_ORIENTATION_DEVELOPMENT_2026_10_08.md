# H2SAFE orientation-class detector-ranking development

## Result

The original geometry-only ranker treated every release as a buoyant vertical
plume. It failed the joint H2SAFE spatial screen, with the horizontal Lab-2
experiment producing a negative rank correlation. A single orientation-class
candidate now keeps the original vertical formula and, for a horizontal
release whose azimuth is not published, penalizes height separation
symmetrically.

Across the same five public full-scale helium-surrogate experiments:

| Metric | Geometry-only baseline | Orientation candidate |
|---|---:|---:|
| Median Spearman correlation | 0.582 | 0.582 |
| Fraction with Spearman correlation at least 0.4 | 0.80 | 1.00 |
| Mean top-five recall | 0.56 | 0.64 |
| Nearest-ranked sensor in strongest-response quartile | 0.60 | 0.80 |
| All four internal reference screens | Fail | Pass |

The horizontal case changes from Spearman `-0.366` to `0.567`. This is a useful
mechanistic correction, but it is **not independent validation**: the candidate
was selected after the original H2SAFE outcomes and failure were known. No
helium concentration was converted to hydrogen concentration, and no detector
amplitude or alarm/trip threshold was fitted.

## Runtime decision

The candidate is frozen as a development model for the next untouched cohort.
It is not used for station detector routing. Runtime keeps the existing
zone-specific near/far mapping and its established concentration multipliers.

The next cohort must declare, in one coordinate frame, the horizontal nozzle
vector, ventilation inlet/outlet coordinates and velocity vectors, obstacles,
signal units and release-time alignment. Passing the internal H2SAFE screens
cannot replace that prospective check.

## Reproduction

With the public archive extracted under the ignored raw-data directory:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts\develop_h2safe_orientation_ranker.py
```

The machine-readable record is
`research/h2safe_orientation_development_2026_10_08.json`.
