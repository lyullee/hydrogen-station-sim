# External validation: ignited enclosure pressure peaking

The prospectively frozen evaluation used the public large-scale dataset
[10.23642/USN.17934047](https://doi.org/10.23642/USN.17934047) associated with
Lach and Gaathaug's study
([10.1016/j.ijhydene.2020.12.015](https://doi.org/10.1016/j.ijhydene.2020.12.015)).
Experiments 2–28 were untouched holdouts. Experiment 1 and experiments 29–31
were excluded before scoring because their traces had been opened previously.

## Result

- Eligible holdouts: **27/27**; identity or channel exclusions: **0**.
- Primary pass: **27/27 (100%)** with absolute peak-overpressure error
  no greater than the frozen 2.0 kPa threshold.
- Peak-overpressure MAE: **0.672 kPa**.
- Maximum peak-overpressure absolute error: **1.796 kPa**.
- Secondary peak-time pass: **21/27**; median relative error: **17.66%**.
- Secondary trace-NRMSE pass: **26/27**; median: **19.43%**.
- Confirmatory component-level decision rule: **PASS**.

| Exp. | Vents | Measured peak (kPa) | Predicted peak (kPa) | Abs. error (kPa) | Peak-time error (%) | Trace NRMSE (%) |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 1 | 4.42 | 4.47 | 0.06 | 3.8 | 19.0 |
| 3 | 1 | 16.70 | 15.60 | 1.10 | 7.4 | 14.8 |
| 4 | 1 | 15.76 | 14.23 | 1.54 | 10.1 | 17.7 |
| 5 | 2 | 5.34 | 6.18 | 0.84 | 14.0 | 20.3 |
| 6 | 2 | 5.08 | 5.94 | 0.86 | 9.0 | 20.4 |
| 7 | 2 | 21.98 | 22.19 | 0.22 | 11.2 | 16.3 |
| 8 | 2 | 20.64 | 20.56 | 0.08 | 13.3 | 16.4 |
| 9 | 3 | 13.98 | 14.50 | 0.52 | 19.9 | 19.0 |
| 10 | 3 | 13.91 | 14.41 | 0.50 | 22.5 | 19.5 |
| 11 | 3 | 14.72 | 15.03 | 0.30 | 21.8 | 18.9 |
| 12 | 3 | 15.17 | 15.47 | 0.30 | 23.5 | 20.1 |
| 13 | 3 | 21.82 | 21.82 | 0.00 | 23.9 | 19.5 |
| 14 | 3 | 21.12 | 21.38 | 0.26 | 23.6 | 19.4 |
| 15 | 3 | 4.31 | 5.21 | 0.90 | 21.1 | 22.8 |
| 16 | 3 | 4.46 | 5.39 | 0.93 | 25.5 | 22.8 |
| 17 | 2 | 32.47 | 33.81 | 1.34 | 35.1 | 17.7 |
| 18 | 2 | 33.21 | 33.52 | 0.31 | 14.0 | 17.5 |
| 19 | 1 | 48.12 | 46.32 | 1.80 | 5.5 | 14.3 |
| 20 | 1 | 46.51 | 45.76 | 0.75 | 4.5 | 13.7 |
| 21 | 2 | 23.67 | 23.78 | 0.11 | 15.3 | 18.2 |
| 22 | 2 | 4.14 | 4.87 | 0.74 | 25.1 | 22.3 |
| 23 | 2 | 3.59 | 4.28 | 0.69 | 27.8 | 24.0 |
| 24 | 3 | 1.85 | 2.32 | 0.47 | 55.4 | 29.5 |
| 25 | 3 | 4.06 | 4.99 | 0.93 | 32.7 | 24.6 |
| 26 | 3 | 10.01 | 10.90 | 0.89 | 17.7 | 22.3 |
| 27 | 3 | 9.79 | 10.71 | 0.92 | 16.8 | 22.3 |
| 28 | 2 | 16.69 | 17.48 | 0.79 | 16.1 | 18.5 |

The peak-pressure endpoint passes strongly. Timing is less accurate for several
low-pressure, large-vent cases, and one trace-NRMSE result exceeds the frozen
secondary limit. Those secondary limitations remain visible and are not used
to weaken or redefine the protocol after observing the data.

## Claim boundary

This is external component validation for an immediately ignited hydrogen
release in a vented enclosure. It supports confined-equipment pressure-hazard
calculation within the tested geometry and flow range. It does not validate an
outdoor H70 station fueling loop, jet-flame radiation distance, emergency
controls, operator response, or SAGA effectiveness. Raw MAT files remain
outside version control; the result records their Dataverse file IDs and MD5s.

## Reproduction

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts\run_usn_17934047_ignited_pressure_peaking.py `
  --raw-directory tmp\usn_17934047 `
  --cases 2-28 `
  --output research\usn_17934047_ignited_pressure_peaking_result_2026_10_08.json
```
