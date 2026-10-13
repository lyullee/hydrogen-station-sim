# PRESLHY E3.1 concentration transport diagnostic — 2026-10-14

This is a post-access measurement diagnostic. It is not an independent
validation result and it does not change detector routing, alarm thresholds,
runtime parameters or the IJHE readiness gates.

## Data and method

- Source: PRESLHY E3.1 DisCha public workbooks, DOI
  [10.35097/1187](https://doi.org/10.35097/1187).
- Six public archives were scanned, containing 33 workbooks and five hydrogen
  concentration channels per workbook (`C3`, `C2`, `C1`, `C1-`, `C4`).
- The workbook vessel-pressure channel defines a stable 0.5% pressure-drop
  onset. Concentration onset is the first sustained crossing of 10% of the
  baseline-to-peak excursion. Peak and onset lags are reported relative to
  that pressure event.
- A 3.75 s correction is subtracted from the observed concentration timestamp
  only. This value is a documented sensor transport/measurement-delay
  diagnostic input; it is not a fitted station parameter.

## Result

| quantity | uncorrected | after 3.75 s timestamp correction |
|---|---:|---:|
| concentration onset lag, median | 4.40 s | 0.65 s |
| concentration onset lag, 10th–90th percentile | 3.44–7.48 s | −0.31–3.73 s |
| concentration peak lag, median | 6.10 s | 2.35 s |
| concentration peak lag, 10th–90th percentile | 4.64–15.92 s | 0.89–12.17 s |

The diagnostic shows that an uncorrected concentration timestamp can make the
detector response appear roughly 3.75 s later than the pressure-defined source
event. The corrected values still contain transport, mixing, spatial and
instrument-response effects; a negative corrected onset is therefore a timing
diagnostic flag, not proof that the detector physically responded before the
release.

## Use boundary

The result supports timestamp annotation and uncertainty handling in analysis
views. It does not justify advancing a live alarm, changing a detector's
location or threshold, or claiming independent station-level validation. A new
pre-access frozen holdout with documented sensor positions, calibration and
transport paths is required before any runtime promotion.

Machine-readable output: `research/preslhy_e31_concentration_transport_diagnostic_2026_10_14.json`.
