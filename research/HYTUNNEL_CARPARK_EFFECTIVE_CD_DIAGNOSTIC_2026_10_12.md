# HyTunnel-CS effective-discharge-coefficient diagnostic

This is a **post-outcome development diagnostic**, not a new validation result. It
uses the same public actual-hydrogen raw time series, one-second aggregation and
eligibility rule as the frozen HyTunnel-CS holdout. The frozen evaluator remains
unchanged at `Cd=0.8`; no runtime parameter, threshold, case, or claim was changed.

The source is the CC BY 4.0 archive [10.23642/USN.14405903](https://doi.org/10.23642/USN.14405903)
and its article [10.3390/en14113008](https://doi.org/10.3390/en14113008). The
article reports that the blowdown experiments were choked at the nozzle and gives a
mass-flow uncertainty of ±0.2% of flow rate.

## Result

| experiment | measured peak (g/s) | frozen prediction (g/s) | effective `Cd` at peak |
|---:|---:|---:|---:|
| 19 | 7.883 | 6.407 | 0.982 |
| 20 | 7.869 | 6.408 | 0.983 |
| 21 | 4.210 | 3.426 | 0.992 |
| 22 | 2.511 | 2.036 | 0.996 |
| 23 | 4.272 | 3.430 | 0.997 |

The frozen model preserves the observed temporal ordering (Spearman 0.996–1.000)
but systematically underpredicts the peak. The implied coefficient is close to
1.0 rather than 0.8. This is evidence of a source-boundary mismatch—such as the
nozzle/line representation or the pressure location used by the aperture model—
and is not evidence that a new coefficient should be fitted to these five cases.

## Paper and runtime boundary

The result is retained as a transparent explanation for the failed 3/5 mass-flow
gate. It cannot be used to promote the HyTunnel claim, validate outdoor station
consequence distances, infer detector placement, or tune the digital-twin runtime.
A future confirmatory protocol must pre-register the coefficient and resolve the
3.86 m discharge-line boundary (or measure nozzle-upstream pressure) before raw
outcomes are accessed.

The machine-readable output is
`research/hytunnel_carpark_effective_cd_diagnostic_2026_10_12.json`.
