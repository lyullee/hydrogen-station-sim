# HIAD expert-study design sensitivity

This calculation was frozen before holdout response collection or expert rating.
It quantifies limitations of the fixed 24-event design; it is not a study result.

| Standardized paired effect | Estimated power | Monte Carlo SE |
|---:|---:|---:|
| 0.00 | 4.9% | 0.15% |
| 0.20 | 15.0% | 0.25% |
| 0.30 | 27.7% | 0.32% |
| 0.40 | 44.1% | 0.35% |
| 0.50 | 62.7% | 0.34% |
| 0.60 | 77.7% | 0.29% |
| 0.80 | 95.7% | 0.14% |
| 1.00 | 99.5% | 0.05% |

## Interpretation

On the prespecified grid, the smallest standardized paired effect reaching at least 80% simulated power is **0.8**.
If zero of 24 events contain unsafe advice, the exact two-sided 95% upper bound for the event-level rate remains **14.2%**.
Repeated generations and multiple reviewers improve measurement stability but do not change the inferential event count of 24.

## Assumptions and limits

- This is a design sensitivity analysis, not an observed effect estimate.
- The 24-event holdout is fixed by the eligible public incident population and frozen split.
- Normal paired differences are a transparent assumption; bounded and tied expert scores may yield different power.
- Repeated generations and reviewer scores are averaged within event; they do not increase the inferential event count.
- Even zero unsafe events cannot establish zero risk; the exact upper confidence bound must be reported.
