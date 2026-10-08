# Molkov hydrogen jet-flame literature benchmark

## Purpose

The runtime now reports a second, explicitly bounded comparison beside HyRAM+: the visible length of a non-premixed hydrogen free-jet flame in still air. It uses the dimensional relation restated by Molkov and Saffers (2011), `L_F = 76 (m_dot d_N)^0.347`, with the consequence model's actual mass flow and the physical leak diameter.

## Reproducible check

`scripts/validate_molkov_jet_flame_correlation.py` transcribes 25 high-pressure Schefer and Proust rows from Table 1. Across that subset, the mean absolute percentage error is 14.32%, the median is 14.74%, 22/25 rows (88%) are within 30%, and the maximum error is 33.06%. The JSON artifact records every row, the source PDF hash, the implementation hash, and the predeclared descriptive screen.

Run:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts\validate_molkov_jet_flame_correlation.py
```

## Claim boundary

This is a same-publication implementation and descriptive comparison, not independent validation by this project. The source publication reports 123 experiments over nozzle diameters of 0.4–51.7 mm and storage pressures from near atmospheric to 90 MPa. Runtime points are marked in-domain only inside the narrower transcribed high-pressure subset envelope of 1–7.94 mm and 1.1–360 g/s.

The value is a visible flame length for a free jet in still air. It is not a radiation harm distance, safety distance, evacuation radius, accident frequency, impinging-jet result, obstructed or confined result, or full-station validation.

## Source

Molkov, V. and Saffers, J.-B. (2011), “The Correlation for Non-Premixed Hydrogen Jet Flame Length in Still Air,” *Fire Safety Science*, 10, 933–943. DOI: [10.3801/IAFSS.FSS.10-933](https://doi.org/10.3801/IAFSS.FSS.10-933).
