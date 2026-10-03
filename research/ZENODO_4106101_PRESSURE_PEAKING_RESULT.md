# Zenodo 4106101 pressure-peaking screen

This is a prospective external consequence-submodel screen using the open
HyTunnel-CS/Zenodo release **Unignited Pressure Peaking Phenomena**
([10.5281/zenodo.4106101](https://doi.org/10.5281/zenodo.4106101)). The
associated publication is [10.1016/j.ijhydene.2020.08.221](https://doi.org/10.1016/j.ijhydene.2020.08.221).

The protocol was frozen before the raw outcome files were downloaded. All ten
experiments (cases 2–11) with pressure and mass-flow channels and documented
vent geometry were retained; no outcome-based case selection or per-case
parameter fitting was used. The runner uses the fixed 14.9 m³ enclosure,
case-documented vent areas and initial temperatures, measured mass-flow input,
constant-temperature ideal-gas balance and fixed discharge coefficient
`C_d = 0.7` documented by the source publication. Raw archives are hash
checked and remain outside git.

The primary thresholds were declared in advance: peak overpressure absolute
error ≤5 kPa and peak-time relative error ≤20% for each case. All ten cases
were eligible. Seven of ten passed both primary metrics (0.70), so the
predeclared ≥80% confirmatory rule was **not met**. The result is therefore an
exploratory consequence-submodel screen, not a confirmatory validation.

Reproduction:

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python.exe scripts/run_zenodo_4106101_pressure_peaking.py `
  --pressure-dir data/public_validation/raw/zenodo_4106101/pressure_unpacked `
  --mfr-archive data/public_validation/raw/zenodo_4106101/HTE242USN00011MFR.zip `
  --output research/zenodo_4106101_pressure_peaking_result.json
```

The detailed machine-readable result is in
`research/zenodo_4106101_pressure_peaking_result.json`, and the frozen
protocol is in `research/zenodo_4106101_pressure_peaking_protocol.json`.

## Claim boundary

This screen covers only unignited pressure peaking in a confined, vented
enclosure. It does not validate the HRS filling loop, cascade/compressor
control, dispenser operation, outdoor dispersion, ignition, emergency
response, or SAGA effectiveness. It does not close the IJHE readiness audit or
permit completion of the broader validated-digital-twin objective.
