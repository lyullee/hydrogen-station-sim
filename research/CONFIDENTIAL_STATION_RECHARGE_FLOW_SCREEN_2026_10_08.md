# Confidential station recharge-flow screen

## Purpose

This privacy-bounded diagnostic tests whether the reference compressor's
initial flow is consistent with owner-controlled station recharge records. It
uses an external tag mapping in memory and publishes no path, filename, tag,
timestamp, raw row, site, company or equipment identity.

The analysis first selects the internally coherent instantaneous/totalizer pair
in each eligible equipment table. Positive-flow segments must last at least 10
seconds and retain compressor-load feedback for at least 80% of the segment.
This separates recharge operation from unrelated or ambiguous flow intervals.

## Result

Seven equipment tables and 567,847 rows were eligible. The screen identified
995 positive-flow intervals, of which 733 met the compressor-load recharge
criterion. Four anonymous valve-state modes covered those recharge intervals.

- Median recharge duration: 108 s
- Conditional average flow, if the cumulative channel unit is kg: 9.594 g/s
- Conditional 10th--90th percentile flow: 6.951--9.916 g/s
- Median integrated-signal/totalizer ratio: 0.9909
- Median derivative-to-signal scale: 0.016640, close to 1/60

The reference compressor predicts 8.689 g/s at 20 MPa(abs), 298.15 K,
8.0e-4 m3/s swept-volume rate and 0.75 volumetric efficiency. This lies inside
the conditional observed 10th--90th percentile range and is 9.44% below its
median.

## Decision

The default compressor flow has conditional station-side face validity and is
retained unchanged. This result does not authorize a fitted capacity multiplier
because the generic channel roles, engineering units, reset/sign convention and
calibration state remain unattested. It is a post-access internal diagnostic,
not an independent holdout or station-to-vehicle validation.

The machine-readable aggregate is
`research/confidential_station_recharge_flow_screen_2026_10_08.json`.
