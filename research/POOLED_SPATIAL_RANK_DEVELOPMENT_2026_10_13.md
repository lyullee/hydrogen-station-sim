# Pooled spatial-rank candidate development (2026-10-13)

## Result

Two already-consumed spatial cohorts were searched together so that the next
candidate would not be chosen from one experiment family alone:

- 18 HyTunnel-CS actual-hydrogen experiments, DOI
  [10.23642/USN.14405903](https://doi.org/10.23642/USN.14405903)
- 5 H2SAFE helium-surrogate files, DOI
  [10.7799/17118570](https://doi.org/10.7799/17118570)

The fixed grid contained 15,120 candidates. Selection maximized the weakest
normalized margin across the four declared screens in both cohorts, followed
by pooled top-five recall and pooled median Spearman. The selected rank-only
candidate is:

```text
exp(0.3*max(dy,0) - 0.1*max(-dy,0))
------------------------------------------------------
0.25 + horizontal_distance_m^1.25 + 0.2*abs(dy)
```

| Cohort | Median Spearman | rho >= 0.4 fraction | Mean top-5 recall | Nearest in top quartile | Joint |
|---|---:|---:|---:|---:|---|
| HyTunnel actual H2 (18) | 0.600 | 0.778 | 0.744 | 0.944 | PASS |
| H2SAFE helium (5) | 0.569 | 0.800 | 0.800 | 0.600 | FAIL |

The candidate passes seven of eight cohort-specific screens. It does not pass
the pooled transfer requirement because only three of the five H2SAFE cases
place the highest-ranked predicted detector in the observed top response
quartile. This failure is retained.

## Freeze and use decision

- Implementation: `src/h2station/prospective_spatial_rank.py`
- Development record:
  `research/pooled_spatial_rank_development_2026_10_13.json`
- Future protocol:
  `research/prospective_spatial_rank_protocol_2026_10_13.json`
- Runtime detector routing remains unchanged and disabled for this candidate.
- The readiness gate is unchanged.
- A new dataset-specific protocol must identify and hash an untouched
  actual-hydrogen cohort before its numerical responses are opened.

This is post-outcome model development. It is not detector-placement
validation, concentration prediction, alarm calibration, CFD, ESD validation,
or a safety-distance result.
