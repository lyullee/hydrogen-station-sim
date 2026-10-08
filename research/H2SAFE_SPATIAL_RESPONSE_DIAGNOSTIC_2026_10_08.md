# H2SAFE spatial-response diagnostic

## Why this was run

The public H2SAFE package provides five full-scale indoor helium-surrogate
release experiments with three-dimensional source and sensor coordinates. Its
CSV clock is not cross-walked to the wall-clock release intervals, so deriving
release onset from the measured response would violate the frozen timing
protocol. This diagnostic therefore uses a time-alignment-free sensor response:
the 99th percentile minus the 10th percentile over each complete trace.

Source: [NLR Data Catalog](https://data.nlr.gov/submissions/330), DOI
[`10.7799/17118570`](https://doi.org/10.7799/17118570). The source license
requires retention of its notice and DOE/NLR/Alliance credit in resulting
publications. Raw files remain in the ignored local data directory.

## Main finding

The published coordinates form repeated physical height bands, including
0.6096 m and 10.2235 m, so Y is the elevation axis. With Y as elevation, the
fixed geometry-only buoyant-gas rank law produced:

- median Spearman rank correlation: **0.582**;
- experiments with Spearman correlation at least 0.4: **4/5**;
- mean top-five recall of the strongest-response quartile: **0.56**;
- nearest-ranked sensor in the strongest-response quartile: **3/5**.

The first two frozen screens passed and the final two failed. The joint spatial
screen therefore **failed**. The horizontal Lab-2 release was the clearest
counterexample (Spearman correlation -0.366), which is consistent with the
rank law omitting nozzle direction, HVAC vectors and obstacles. Treating Z as
elevation reduced median correlation further, confirming that coordinate-axis
interpretation materially affects the result.

## Runtime decision

The station assigns every release to a zone-specific “near” and “far” detector.
The coordinate-only alternative was rejected because it failed the joint
screen and, without wall, nozzle-vector and HVAC information, could route a
release to a distant elevated detector in another process area. The runtime
therefore retains the existing zone mapping, 1.0 and 0.45 concentration
multipliers, public hydrogen concentration proxy, and alarm/trip thresholds.
No helium amplitude or threshold is transferred.

Every result exposes
`EVALUATED_NOT_APPLIED_FAILED_JOINT_SCREEN` and the failed-screen claim limit
to the LLM evidence manifest and API health response. This prevents a failed
development model from silently changing alarms while retaining the exact
evidence needed for a later orientation/HVAC/obstacle-aware model.

## Reproduction

With the source archive extracted under the ignored data directory:

```powershell
.\.venv\Scripts\python.exe scripts\run_h2safe_spatial_response_diagnostic.py
```

The machine-readable output is
`research/h2safe_spatial_response_diagnostic_2026_10_08.json`.
