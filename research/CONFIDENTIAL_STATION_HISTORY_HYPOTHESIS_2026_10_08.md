# Confidential station longitudinal-history diagnostic

This privacy-bounded diagnostic recovered two stable structures from the 25
previously underused nine-column station history exports. It publishes no raw
row, tag, path, filename, absolute timestamp, calendar date, company, site or
manufacturer.

The 25 files contain 58,618,833 data rows at a median one-second sample period.
The pressure/flow candidate structure covers 12 files and 29,361,269 rows. The
thermal candidate structure covers 13 files and 29,257,564 rows. Their observed
time coverage overlaps by 99.7837%. A deterministic 600-row stride retained
97,709 aggregate-only diagnostic samples.

For the pressure/flow structure, the chronological first 70% and last 30% were
compared without fitting. The holdout medians for both flow-like candidates,
two lower-pressure candidates and the already separately attested medium/high
storage-pressure roles all stayed inside the calibration P05--P95 envelopes.
The lower/medium/high candidate ordering held in 99.9142% of sampled rows.
Cumulative counter candidates were intentionally excluded from an envelope
stability test because their expected monotonic increase makes a later median
larger by construction.

For the thermal structure, all five temperature-like holdout medians stayed
inside their calibration P05--P95 envelopes. Every sampled value in those five
channels stayed inside the deliberately broad exploratory range of -80 to
120 raw units. Their roles and units remain unattested, so this result supports
only long-term numerical stability and temperature-like plausibility.

The result establishes that the large local archive is useful station-side
longitudinal evidence. It does not authorize a flow unit, totalizer unit,
temperature role, runtime parameter update, vehicle-fill claim, safety limit or
consequence-distance claim. No vehicle-side channel was confirmed. The
machine-readable aggregate is
`confidential_station_history_hypothesis_2026_10_08.json`.
