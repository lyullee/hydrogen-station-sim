# Woodfield metal-tank heat-transfer development check

## Result

The experiment is reported by Woodfield et al. (DOI `10.1299/jtst.2.180`). A pinned HydDown checkout at commit
`1040d758b819533451086baa5cf2a47b4292a22f` was used to replay its
Woodfield hydrogen filling and discharge cases. The local station
mixed-convection formulation was fixed in commit `91698f51`, before this
comparison. No coefficient was fitted to the Woodfield outcomes.

| Experiment | Model | Pressure RMSE | Temperature sensor-envelope RMSE |
|---|---|---:|---:|
| Filling | natural convection only | 13.218 bar | 24.098 K |
| Filling | station mixed convection | 9.187 bar | 7.656 K |
| Discharge | natural convection only | 1.062 bar | 9.034 K |
| Discharge | station mixed convection | 1.062 bar | 9.034 K |

During filling, the existing inlet-forcing term reduced pressure RMSE by
**30.50%** and temperature envelope RMSE by **68.23%** relative to the
otherwise identical natural-convection calculation. During discharge there is
no positive inlet flow, so the forcing term remained inactive and the two
results were numerically identical. All four mass and energy conservation residuals were below 1e-12. This is the intended physical separation
between filling-jet mixing and vessel blowdown.

## Reproducibility and rights boundary

The runner verifies the exact HydDown Git commit and SHA-256 hashes of both
case files. It uses the source-declared geometry, material inventory, mass-flow
history, orifice and ambient boundaries. The repository stores only source
metadata and aggregate errors. It does not retain measurement rows, arrays,
local paths or publisher figures.

The HydDown repository is MIT licensed. The embedded experimental arrays are a
secondary transcription of the original measurements, whose redistribution
rights were not independently established. The JSON artifact therefore records
hashes and metrics only.

## Claim boundary

This is a **post-access model-development diagnostic**. The same publication underlies the mixed-convection mechanism, so this is not an independent confirmation of that mechanism. It supports the
mechanistic use of an inlet-forced heat-transfer term and shows that the same
term correctly becomes inactive during discharge. It does not convert the
failed prospective Type-III result into a pass, select a production default, or
validate the station-to-vehicle loop. A new independent Type-III/IV filling
trace must be prospectively frozen before numerical outcome access.

## Files

- Runner: `scripts/run_woodfield_metal_tank_heat_transfer_development.py`
- Aggregate result:
  `research/woodfield_metal_tank_heat_transfer_development_2026_10_08.json`
