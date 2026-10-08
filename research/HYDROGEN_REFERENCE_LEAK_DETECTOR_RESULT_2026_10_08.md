# Prospective physical-H₂ reference-leak detector result

The analysis protocol and thresholds were committed before the public Excel outcomes were downloaded or opened. The source workbook identity matches the published Zenodo MD5.

- Status: **COMPLETED_FROZEN_PROTOCOL_PASS**
- Physical H₂ observations: **45**
- Joint frozen-screen pass: **True**
- Source: [Zenodo 10.5281/zenodo.12180368](https://doi.org/10.5281/zenodo.12180368)
- Related IJHE article: [DOI 10.1016/j.ijhydene.2024.04.328](https://doi.org/10.1016/j.ijhydene.2024.04.328)

| Detector series | n | Levels | Spearman ρ | Pairwise concordance | Complete | Pass |
|---|---:|---:|---:|---:|---:|---:|
| portable_hydrogen_sniffer | 27 | 3 | 0.943 | 1.000 | 1.000 | True |
| msld_vacuum | 9 | 3 | 0.969 | 1.000 | 1.000 | True |
| msld_sniffer | 9 | 3 | 0.949 | 1.000 | 1.000 | True |

## Magnitude behavior retained as a limitation

The protocol did not require magnitude agreement. The table below preserves the observed median/reference ratios so that a strong ordering result cannot hide detector bias.

| Detector series | Reference (mbar·L/s) | n | Median/reference | Median relative error |
|---|---:|---:|---:|---:|
| portable_hydrogen_sniffer | 1.390e-06 | 9 | 0.892 | -10.8% |
| portable_hydrogen_sniffer | 1.740e-05 | 9 | 0.512 | -48.8% |
| portable_hydrogen_sniffer | 8.230e-05 | 9 | 0.416 | -58.4% |
| msld_vacuum | 1.390e-06 | 3 | 1.086 | +8.6% |
| msld_vacuum | 1.740e-05 | 3 | 0.862 | -13.8% |
| msld_vacuum | 8.230e-05 | 3 | 0.863 | -13.7% |
| msld_sniffer | 1.380e-06 | 3 | 0.058 | -94.2% |
| msld_sniffer | 1.730e-05 | 3 | 0.049 | -95.1% |
| msld_sniffer | 8.200e-05 | 3 | 0.048 | -95.2% |

## Decision

The two tested detector classes preserve the ordering of the three physical hydrogen reference leaks under the frozen screens. This supports a bounded monotonic-response claim only. No detector amplitude, alarm threshold, trip threshold or spatial-routing parameter was changed.

## Claim boundary

This protocol evaluates detector response ordering to physical hydrogen reference leaks. It cannot validate the station spatial detector map, concentration magnitude, alarm or ESD setpoints, release physics, consequence distance, vehicle filling, or the full digital twin.
