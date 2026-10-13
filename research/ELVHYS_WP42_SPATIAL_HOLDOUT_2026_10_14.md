# ELVHYS WP4.2 actual-hydrogen spatial holdout

The public ELVHYS WP4.2 archive (DOI `10.18710/JXJP0H`, CC0 1.0) was evaluated with the frozen `pooled_spatial_rank_v1` candidate on a disjoint cohort. Existing overlap cases 29, 30, 31 and 45 were excluded before scoring. Raw files remain outside Git; the repository stores aggregate metrics and source hashes only.

The cohort contained 29 eligible cases and no ineligible cases. The fixed release window was derived only from `PT1ReleaseRig` pressure using q90/q99 thresholds recorded in `research/elvhys_wp42_release_window_amendment_2026_10_14.json`.

| Metric | Result | Screen |
| --- | ---: | --- |
| Median within-case Spearman rank | 0.218 | FAIL (≥ 0.5) |
| Cases with Spearman ≥ 0.4 | 27.6% | FAIL (≥ 60%) |
| Mean top-5 recall | 0.421 | FAIL (≥ 0.6) |
| Nearest-success fraction | 89.7% | PASS (≥ 0.7) |

The result is therefore retained as a negative diagnostic finding. It does not validate concentration magnitude, detector timing, outdoor hydrogen-station placement, consequence distance, ESD behavior, field safety, or station-to-vehicle operation. The candidate remains disabled for runtime risk visualization until an independent spatial model or a locked revised candidate passes its predeclared screens.

See `research/elvhys_wp42_spatial_holdout_result_2026_10_14.json` for the machine-readable result and `research/elvhys_wp42_spatial_holdout_protocol_2026_10_14.json` for the frozen case and claim boundary.
