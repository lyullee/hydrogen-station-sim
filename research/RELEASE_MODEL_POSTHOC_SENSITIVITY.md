# Release-model post-hoc sensitivity diagnostic

This report is development evidence only. The frozen Schefer 2006/2007 and Grune 2014 holdout results were not changed and no grid point is a new validation claim.

| Case | Baseline Cd | Best grid Cd | NRMSE | Median APE | Half-time error | Any joint pass |
|---|---:|---:|---:|---:|---:|---|
| `schefer_2006_mass_flow` | 1 | 1 | 5.83% | 22.85% | 28.29% | false |
| `schefer_2007_pressure` | 1 | 1 | 11.58% | 27.46% | 6.51% | false |
| `grune_2014_pressure` | 0.8 | 0.4 | 3.36% | 3.30% | n/a | false |

## Interpretation

The declared grid does not produce a joint pass for any of the three traces. The Schefer 2006 and 2007 minima remain at the locked coefficient, while the Grune startup metrics improve at a lower coefficient but its half-pressure endpoint is unavailable. This points to missing model structure (line-pack, wall heat transfer and/or valve dynamics) rather than a defensible single global discharge coefficient.

The results do not authorize post-hoc parameter replacement in the production twin. A revised model must be frozen before a new external dataset is opened.
