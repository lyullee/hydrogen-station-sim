# USN orientation-class spatial transfer diagnostic (2026-10-14)

This record reproduces the frozen `orientation_class_rank_v2` detector-ranking
formula on 22 public actual-hydrogen experiments from the USN open-ended
rectangular-channel dataset. The runner is
`scripts/audit_usn_orientation_class_transfer_diagnostic.py` and the machine
readable result is
`research/usn_orientation_class_spatial_transfer_diagnostic_2026_10_14.json`.

The source is DOI [10.23642/USN.26117989.v2](https://doi.org/10.23642/USN.26117989.v2),
with the related article DOI
[10.1016/j.jlp.2025.105669](https://doi.org/10.1016/j.jlp.2025.105669). It
contains actual-hydrogen concentration traces from 29 sensors per archive.
The raw archives remain outside Git; the result stores SHA-256 hashes and
derived metrics only.

## Result

Using the complete published trace for each sensor (`q99 - q10`) and the
frozen coordinate mapping `candidate(x,y,z) = dataset(x,z,y)`:

| Metric | Result | Screen |
| --- | ---: | --- |
| Experiments | 22 | 22 required |
| Median Spearman rank correlation | 0.6714 | >= 0.5 PASS |
| Cases with rho >= 0.4 | 95.5% | >= 60% PASS |
| Mean top-five recall of observed top quartile | 87.3% | >= 60% PASS |
| Nearest predicted sensor in observed top quartile | 95.5% | >= 70% PASS |

All four reference screens pass. One case (`23_FFI_P101_T00006`) misses the
nearest-sensor screen while retaining a positive rank correlation (rho 0.567).

## Evidence boundary

This is a **post-access reproducibility and transfer diagnostic**, not a new
independent holdout. The same public dataset had already been opened and used
in repository spatial diagnostics before this record was written. The model
was frozen at commit `2056c04` and no coordinate, amplitude, alarm threshold,
or rank parameter was fitted in this run, but chronology prevents promotion of
this result to the independent-validation gate.

The result does not validate outdoor hydrogen-station detector placement,
concentration amplitudes, alarm or trip setpoints, CFD, consequence distances,
ESD effectiveness, or a synchronized station-to-vehicle loop. Runtime detector
routing remains unchanged.

