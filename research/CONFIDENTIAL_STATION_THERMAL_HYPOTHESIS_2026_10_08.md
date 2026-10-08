# Confidential station thermal mapping-hypothesis diagnostic

## Purpose and evidence boundary

The thermal method and 70/30 chronological split were frozen before numerical
outcome access. The proposed generic temperature roles and cooling-state value
were then evaluated without smoothing, imputation, parameter fitting or raw-row
publication. A custodian has not attested those roles, units, state semantics or
calibration records, so this artifact is a conditional numerical diagnostic and
cannot be promoted to a station thermal validation result.

## Result

Eight equipment logs contributed 653,442 one-second rows. The 70% prefix
contained 457,405 rows and the 30% suffix contained 196,037 rows. All three
suffix medians remained inside the corresponding prefix p05--p95 envelope, the
active cooler temperature-drop median remained inside its prefix envelope, and
neither partition produced a quality warning.

Under the unattested mapping hypothesis:

- compressor temperature median changed from 32.1 to 34.2 degC;
- cooling-active inlet median was -32.8 degC in both partitions;
- cooling-active outlet median changed from -33.7 to -33.3 degC;
- cooling-active temperature-drop median changed from 1.1 to 0.5 degC;
- cooling-active duty cycle changed from 43.5% to 39.2%.

## Decision

The frozen mapping hypothesis is numerically stable within the controlled
record. Runtime parameters remain unchanged, and station thermal-envelope,
precooler-capacity, vehicle-fill, full-loop and safety claims remain disabled.
Custodian confirmation of roles, units, state semantics and calibration is
still required.

The machine-readable aggregate is
`research/confidential_station_thermal_hypothesis_2026_10_08.json`.
