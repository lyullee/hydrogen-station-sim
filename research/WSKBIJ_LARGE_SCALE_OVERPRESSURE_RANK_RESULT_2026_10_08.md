# WSKBIJ large-scale actual-hydrogen overpressure-rank result

Decision: **FAIL**

The frozen screen compares the locked HyRAM+ 6.1 BST relative-severity ordering with a public large-scale actual-hydrogen delayed-ignition campaign.

## Primary screens

| Screen | Value | Threshold | Pass |
|---|---:|---:|---|
| `pooled_spearman_rank_correlation` | 0.5717 | >= 0.5000 | **True** |
| `within_stratum_rank_spearman` | -0.0231 | >= 0.4500 | **False** |
| `within_stratum_pairwise_order_concordance` | 0.4207 | >= 0.6500 | **False** |
| `within_stratum_top_third_recall` | 0.2941 | >= 0.5000 | **False** |
| `scored_case_count` | 44 | >= 40 | **True** |

## Cohort

- Eligible before the minimum-stratum rule: **45**
- Scored cases: **44**
- Retained strata: **6**
- Case replacement: **none**
- Runtime or threshold update after access: **none**

## Diagnostic interpretation

The frozen model passed the pooled rank screen but failed every geometry-controlled rank screen. Its standardized nearest-location BST endpoint occupied a narrow band while the measured peaks varied by more than two orders of magnitude. Reservoir pressure and nozzle diameter alone therefore do not preserve case ordering when obstacle configuration and ignition location vary; no runtime parameter was changed.

- Measured peak range: **0.220--235.390 kPa**
- Predicted peak range: **22.091--22.740 kPa**

## Freeze and provenance

- Dataset: <https://doi.org/10.18710/WSKBIJ>
- License: `CC0 1.0`
- Protocol commit: `d7d979ad75cfeb0e6e6da414e329b59f80049d75`
- Publisher workbook SHA-256 matched: **True**
- Locked model hashes matched: **True**

## Interpretation boundary

A PASS would support relative source-severity ordering by the locked runtime across this large-scale actual-hydrogen campaign. It would not validate absolute overpressure, impulse, obstacle effects, ignition-location effects, sensor-distance attenuation, outdoor HRS geometry, explosion probability, injury distance, full-loop dynamics, emergency decisions or regulatory compliance. A FAIL remains part of the evidence record and these outcomes may not be tuned and reused as fresh validation.

The protocol disclosed that aggregate outcome range and completeness were known before freeze; individual outcome ordering and model residuals were not used to design the analysis.
