# HyTunnel spatial-rank candidate sensitivity (2026-10-11)

This record is a post-outcome development diagnostic. It does not replace the
frozen spatial holdout, enable runtime detector routing, or increase the IJHE
readiness score.

## Finding

The existing geometry rank uses a strong upward buoyancy term and a squared
horizontal-distance denominator. On the 18 public actual-hydrogen HyTunnel
cases it has a mean top-five recall of **0.578** and fails the joint screen.

A declared sensitivity grid found a simpler candidate whose same-cohort screen
passes:

`exp(0.2·max(dy,0) − 1.0·max(−dy,0)) / (0.25 + horizontal_distance + |dy|)^1.25`

| model | median Spearman | mean top-five recall | nearest-success fraction | joint screen |
|---|---:|---:|---:|---|
| frozen rank | 0.560 | 0.578 | 0.944 | FAIL |
| post-outcome candidate | 0.514 | 0.744 | 0.944 | PASS |

The candidate is **not** a validation result. Its coefficients were selected
after the existing responses were visible, so the apparent improvement is
optimistic and cannot revise the frozen gate. The result does, however, turn
the current failure into a concrete next experiment: freeze this exact formula
before obtaining a new independent spatial cohort with the release orientation,
HVAC vector, source coordinates, sensor coordinates and per-sensor response in
one frame.

## Runtime decision

- Frozen production rank remains unchanged.
- No alarm, trip, ESD, concentration multiplier or safety-distance parameter was
  changed.
- The LLM must describe this as a post-outcome candidate, not as validated
  detector placement.

## Reproducibility

- Runner: `scripts/run_hytunnel_spatial_candidate_sensitivity.py`
- Artifact: `research/hytunnel_spatial_candidate_sensitivity_2026_10_11.json`
- Frozen comparison: `research/hytunnel_spatial_holdout_protocol_2026_10_08.json`
- Dataset: [10.23642/USN.14405903](https://doi.org/10.23642/USN.14405903)
