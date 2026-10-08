# WSKBIJ large-scale actual-hydrogen overpressure-rank protocol

## Frozen question

Does the already locked HyRAM+ 6.1 BST runtime preserve relative explosion
severity across an independent large-scale, open-atmosphere, actual-hydrogen
delayed-ignition campaign?

The protocol is frozen before any case-level pressure values are displayed,
ranked against the model or used to calculate a metric. An earlier provenance
inventory did machine-read those cells to produce only aggregate coverage,
range and completeness counts. This is therefore a prospectively fixed
aggregate-access analysis, rather than a strictly outcome-unseen holdout.

## Cohort and endpoints

The publisher workbook contains 51 numbered experiments. Publisher annotations
exclude one no-ignition test and five self-ignition tests from the controlled
delayed-ignition cohort. A row must retain at least one finite value across the
four pressure sensors. Strata are fixed by instrumentation era (experiments
1–27 versus 28–51), nozzle diameter and controlled ignition-position code;
strata with fewer than three cases are not scored. This yields an expected 44
scored cases without inspecting pressure magnitude or order.

For every eligible row, the measured endpoint is the largest finite published
pressure peak across the four sensors. The predicted endpoint is the largest
HyRAM BST overpressure at fixed 0.5, 1, 2 and 3 m locations. Published nozzle
diameter and reservoir gauge pressure are the only case-varying source inputs.
Ambient and hydrogen temperatures are fixed at 293.15 K because the publisher
states that ambient weather was not documented. No case-specific fitting,
obstacle adjustment or ignition-position adjustment is allowed.

## Frozen decision

The result passes only when all of the following hold:

- pooled Spearman rank correlation is at least 0.50;
- within-stratum rank Spearman correlation is at least 0.45;
- within-stratum pairwise order concordance is at least 0.65;
- within-stratum top-third recall is at least 0.50; and
- at least 40 cases remain scored.

Ten thousand stratified bootstrap replicates are diagnostic and do not replace
the fixed thresholds. Cases, thresholds, runtime settings and observation
locations cannot change after outcome access. Failure is retained and cannot be
tuned on these outcomes and relabelled as validation.

## Evidence boundary

A pass supports relative source-severity ordering for this campaign. It does not
validate absolute blast pressure, obstacle or ignition-position physics,
sensor-distance attenuation, injury distance, site geometry, explosion
frequency, the complete station-to-vehicle loop, emergency decisions or
regulatory compliance.

- Dataset: <https://doi.org/10.18710/WSKBIJ>
- License: CC0 1.0
- Machine-readable protocol:
  `research/wskbij_large_scale_overpressure_rank_protocol_2026_10_08.json`
