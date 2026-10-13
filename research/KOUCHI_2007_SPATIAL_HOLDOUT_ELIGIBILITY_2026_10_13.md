# Kouchi 2007 spatial holdout eligibility result

Decision: **INELIGIBLE — model not evaluated**.

The official 10-page ICHS 2007 paper is a real, public, actual-hydrogen source.
It reports five steady dispersion release conditions (20 or 40 MPa; 0.25–2.0
mm apertures) and one 40 MPa, 0.2 mm fast concentration-fluctuation condition.
The steady campaign used eight downwind poles with five sensors per pole; the
fluctuation campaign reports eleven downstream measurement distances.

The detailed source was opened only after the eligibility and decision rules
had been committed in `b47ba31`. The commit occurred at 14:55:51 UTC and the
download started at 14:56:11 UTC. The protocol's manually entered `frozen_at`
value was later than both events, so it is retained as a clerical error and an
immutable chronology amendment records the Git and file-system times. The
official PDF has SHA-256
`a80ab4303b8f5f167fe1cb1fac7d38e6e46c92199be669b46f2914607aa5b4ec`.
The PDF is not committed because redistribution rights are not explicit.

The source fails two frozen requirements:

- at most six distinct release cases are available, below the required ten;
- the complete per-observation numerical concentrations are not published as a
  machine-readable table or raw time series.

The `pooled_spatial_rank_v1` model was therefore not run. Values were not
digitized after the case-count failure was known, points from different releases
were not pooled, and no coefficient, coordinate, threshold, case scope, API, or
runtime setting changed. The existing spatial detector transfer gate remains a
transparent failure.

The source remains useful as bounded evidence that actual-hydrogen concentration
and fluctuation measurements cover 20–40 MPa and 0.2–2.0 mm apertures. It does
not validate detector placement, concentration magnitude, alarm thresholds,
consequence distances, or field safety.
