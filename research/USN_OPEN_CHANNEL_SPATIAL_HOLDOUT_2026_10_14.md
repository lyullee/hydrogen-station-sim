# USN open-channel spatial holdout protocol (2026-10-14)

This protocol originally froze the spatial detector and eligibility rules for
the public USN Figshare dataset
[`10.23642/USN.26117989.v2`](https://doi.org/10.23642/USN.26117989.v2). The
dataset advertises actual-hydrogen dispersion experiments with filling
pressure, temporal mass flow and 29 concentration sensors. It is licensed CC
BY 4.0. The related article is DOI `10.1016/j.jlp.2025.105669`.

The existing `orientation_class_rank_v2` candidate is used exactly as frozen in
`src/h2station/spatial_detector.py`. No coordinate, source-strength, alarm or
rank-parameter fitting is permitted. The raw archives remain outside Git; the
repository will retain only source metadata, file hashes, eligibility results
and aggregate derived metrics.

At least 18 independent experiments must expose the source and sensor
coordinates in one frame, a release marker, and at least 30 finite samples per
sensor. Missing coordinate or per-sensor numeric channels make the source
context-only and no spatial score is run. A pass requires every eligible case
and all four frozen aggregate screens: median Spearman rho >= 0.5, at least 60%
of cases with rho >= 0.4, mean top-five recall >= 0.6, and nearest-sensor
success >= 0.7.

The source was subsequently opened and was found to have already been used in a
prior post-access spatial diagnostic. The protocol is therefore **reclassified
as not independent** and does not change the readiness gate. The reproducible
run is recorded in
`research/USN_ORIENTATION_CLASS_SPATIAL_TRANSFER_2026_10_14.md` and its JSON
artifact. Even a pass supports only component spatial-rank transfer in the
published open-channel geometry. It does not validate outdoor hydrogen-station
detector placement, concentration amplitudes, alarm/trip thresholds, CFD,
ESD, consequence distances or a complete station-to-vehicle loop.
