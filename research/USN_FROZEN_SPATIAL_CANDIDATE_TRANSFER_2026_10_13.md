# USN actual-H2 frozen spatial-candidate transfer diagnostic

This report evaluates `pooled_spatial_rank_v1` without coefficient tuning on
22 public actual-hydrogen open-channel experiments from
<https://doi.org/10.23642/USN.26117989>. The dataset was not included in the
15,120-candidate numerical search. Its outcomes had nevertheless been inspected
before the candidate freeze, so this is a **post-access transfer diagnostic**,
not independent or prospective validation.

## Fixed result

| Screen | Result | Threshold |
|---|---:|---:|
| Median Spearman rank correlation | 0.658 | >= 0.5 |
| Fraction of cases with Spearman >= 0.4 | 72.7% | >= 60% |
| Mean top-five detector recall | 72.7% | >= 60% |
| Nearest detector in observed response quartile | 54.5% | >= 70% |

The first three screens pass and the nearest-detector screen fails. The joint
result is therefore **FAIL** and is retained as such. The repeated failure on
the nearest-detector endpoint shows that distance and buoyancy alone can rank a
useful detector set, but cannot justify a single-nearest-detector placement
rule across different channel geometries and release orientations.

## Coordinate and evidence controls

- Dataset coordinates use `x=width`, `y=streamwise`, `z=height`.
- The frozen candidate declares `y=elevation`; the evaluation therefore uses
  `candidate(x,y,z) = dataset(x,z,y)` in metres.
- The response is each sensor's full-trace `q99 - q10` concentration range.
- Candidate coefficients, implementation hash, protocol hash and development
  artifact hash are recorded in the JSON result.
- No coefficient was tuned and no API, HAZOP or detector runtime parameter was
  changed.

## Claim boundary

This diagnostic does not validate hydrogen concentration, alarm time, detector
placement, CFD, ESD, flammable volume, safety distance or complete-station
behavior. A new untouched actual-hydrogen cohort satisfying the frozen protocol
is still required before any prospective validation claim or runtime use.
