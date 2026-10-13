# Prospective spatial-rank candidate freeze (2026-10-13)

`pooled_spatial_rank_v1` is now fixed for a future actual-hydrogen spatial
holdout. The candidate uses only common-frame source and sensor coordinates,
with `y` declared as elevation. It returns a within-case order and no physical
concentration.

The future cohort must contain at least ten eligible hydrogen-release cases
and at least eight usable sensors per case. Source and detector coordinates,
the time crosswalk, per-sensor numerical concentration, release orientation,
and ventilation state must be publisher-authenticated. Every eligible case in
the frozen scope is retained.

All four screens must pass without coefficient or threshold changes:

1. median Spearman rank correlation at least 0.5;
2. at least 60% of cases with Spearman correlation at least 0.4;
3. mean top-five recall of the observed response quartile at least 0.6; and
4. the highest-ranked predicted sensor in the observed response quartile in at
   least 70% of cases.

The generic freeze is not yet a dataset-specific pre-access protocol. When a
new candidate dataset is found, its DOI, exact files, case scope, hashes and
download timestamp must be added before numerical outcomes are accessed. A
failure remains a failure and cannot be repaired by dropping cases after
inspection.

The exact machine-readable contract is in
`research/prospective_spatial_rank_protocol_2026_10_13.json`.
