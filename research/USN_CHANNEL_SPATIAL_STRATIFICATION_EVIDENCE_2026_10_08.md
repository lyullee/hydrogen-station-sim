# USN/FFI actual-hydrogen spatial stratification evidence

Generated: `2026-10-08T05:07:49.868146+00:00`

## Decision

This is post-access descriptive evidence, not an independent detector-map validation.

- Experiments: **22**
- Sensors per experiment: **29**
- Sensor-case observations: **638**
- Top sensors: alarm/trip coverage **100.0% / 100.0%**
- Near-source bottom sensors: median alarm latency **10.67 s** under the downward jet
- Top placement had the highest case mean in **20/22** tests

## Engineering interpretation

The physical-H2 records support layered coverage in this confined geometry: ceiling detection for the sustained buoyant layer, supplemented by near-source coverage along the downward jet path. Exact station locations and outdoor transfer remain unvalidated.

## Placement results

| Placement | Observations | Median steady H2 | Alarm coverage | Median alarm latency | Trip coverage |
|---|---:|---:|---:|---:|---:|
| top | 286 | 9.572 vol% | 100.0% | 18.01 s | 100.0% |
| mid-high | 110 | 3.616 vol% | 92.7% | 19.25 s | 77.3% |
| mid-low | 110 | 0.440 vol% | 68.2% | 34.29 s | 47.3% |
| bottom | 132 | 0.274 vol% | 78.0% | 11.32 s | 70.5% |

## Claim boundary

Twenty-two physical-hydrogen tests support a descriptive layered-placement rationale inside this open-ended 5.8 m channel: ceiling probes provide broad sustained coverage, while probes in the downward-jet path can respond earlier. Because outcomes were accessed before this analysis was designed, this is not independent validation and cannot validate an outdoor station detector map, alarm setpoints, ESD effectiveness, runtime spatial routing, or the full digital twin.

## Sources

- Dataset: https://doi.org/10.23642/usn.26117989.v2
- Article: https://doi.org/10.1016/j.jlp.2025.105669
