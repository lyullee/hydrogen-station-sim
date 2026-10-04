# USN ignited-release thermal-effects archive: post-freeze replay

This record documents the first post-freeze read of the public USN/Figshare
archive **Experimental data – hydrogen safety, thermal effects**
([DOI 10.23642/usn.17695082.v1](https://doi.org/10.23642/usn.17695082.v1)).
The dataset is CC BY 4.0 and contains eight MATLAB v7.3 experiment files with
mass flow, source pressure/temperature, heat-flux channels, thermocouples and
ventilation channels. The source description covers 350/700 bar releases,
0.5/1.0 mm release devices and forced ventilation in a semi-confined
container.

## Reproducible extraction

`scripts/audit_thermal_effects_ignited_release.py` reads every public
`Exp_00001.mat` through `Exp_00008.mat` file. It does not select cases after
looking at outcomes. For each file it records the SHA-256 digest, HDF5 group
and channel inventory, strict monotonicity and sampling interval of each time
base, source-pressure/temperature ranges, mass-flow range, heat-flux ranges,
and temperature-channel ranges. The active release window is the longest
contiguous interval with `MFM/mfr >= 0.5 g/s`; this is a declared noise-boundary
rule, not a fitted event cutoff.

The derived JSON is
`research/thermal_effects_ignited_release_result_2026_10_05.json`. The raw
MAT files remain external and are not committed to Git.

## Observed archive-level checks

- 8/8 selected files were present and parsed.
- Every case has the required mass-flow, source pressure/temperature,
  ventilation and heat-flux groups; the temperature-sensor group is absent
  only in `Exp_00003.mat`, as recorded rather than imputed.
- All retained time bases are strictly increasing.
- The observed peak mass-flow range is 4.036–13.004 g/s and the recorded source
  pressure maxima span approximately 356–710 bar.
- The archive contains large differences in heat-flux and temperature peaks,
  which are retained as measured outcomes rather than collapsed into a single
  “typical” case.

## Claim boundary

This is a **descriptive, post-freeze consequence-data replay**, not predictive
validation of the production HyRAM adapter. The public record does not expose
a frozen case-to-case mapping of nozzle diameter, release angle, exact source
boundary and sensor geometry sufficient for an untouched model comparison.
Consequently this record makes no parameter fit, CFD calibration, station
full-loop, controller, LLM-effectiveness or legal separation-distance claim.
The next valid step is an author-confirmed mapping or an independent raw
logger release, followed by a separately frozen model-comparison protocol.

## Reproduction

```powershell
.\.venv\Scripts\python.exe scripts/audit_thermal_effects_ignited_release.py `
  <external-raw-directory> `
  --output research/thermal_effects_ignited_release_result_2026_10_05.json
```

The corresponding source record and license are linked above; cite the dataset
and the associated IJHE study separately when using the measurements.
