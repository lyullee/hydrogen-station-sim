# Grune/Sempert mechanical-ventilation and H2-dispersion dataset

## Decision

This dataset is accepted as an independent **ventilation, dispersion and detector-placement validation lead**. It is not counted as an external full-loop hydrogen-refuelling validation set for the IJHE readiness gate.

The distinction is deliberate: the files contain spatial hydrogen concentration and flow-field measurements for confined-space mechanical-ventilation cases, but they do not contain the synchronized vehicle/cascade/compressor/precooler/dispenser controller traces required to validate the station protocol and control loop.

## Provenance and rights

- Record: [Zenodo 4668554](https://zenodo.org/records/4668554)
- DOI: [10.5281/zenodo.4668554](https://doi.org/10.5281/zenodo.4668554)
- Title: *Efficiency of mechanical ventilation on H2 dispersion (PS)*
- Authors: Joachim Grune and Karsten Sempert, Pro-Science GmbH
- Publication date: 2021-04-07
- License: CC BY 4.0
- Grant context: European Commission H2020 HyTunnel-CS, grant 826193
- Archive size: 11,108,400 bytes

Raw files are not copied into this repository. The repository records the immutable Zenodo identifiers and MD5 values so a future reproduction can download the source and verify its identity.

| File | Bytes | MD5 |
| --- | ---: | --- |
| `HTE2440PS000MIXED_300321.pdf` | 706,086 | `d4b59189dd4017c695cc652f4f572128` |
| `HTE2440PS001MIXED_300321.xlsx` | 52,610 | `da176772755b1a2449a76df9e12b9cd3` |
| `HTE2440PS002MIXED_300321.xlsx` | 65,696 | `20f996be57fc3d8cf7d091d1f982bd75` |
| `HTE2440PS003MIXED_300321.xlsx` | 50,590 | `953b6a033553288831b1ee02b881dbec` |
| `HTE2440PS004MIXED_300321.xlsx` | 81,649 | `093d3d8e6ef030615704ee9096d3d84f` |
| `HTE2440PS005FLMT00300321.xlsx` | 26,724 | `c4b9195a2bb89213eda9aa2ac9e9ec07` |
| `HTE2440PS006MIXED_300321.zip` | 11,108,400 | `ade3911c0df50ee70486153455f4bd12` |

## Recorded scope

The workbook families cover 1 mm and 4 mm hydrogen releases, several release rates, no-wind and wind cases, and co-, counter- and cross-flow ventilation. The supplied data include spatial H2 concentration points, flow-field information and facility/CAD context. A separate flow-meter workbook supports the wind-field interpretation.

The data can support a pre-registered check of:

1. qualitative and quantitative dilution under mechanical ventilation;
2. detector placement and alarm-zone coverage;
3. the direction and persistence of accumulation under different ventilation and wind cases;
4. the digital twin's visualization and consequence-layer behavior for a confined-space release.

It cannot support claims about vehicle filling, cascade pressure management, compressor/precooler dynamics, dispenser control, SOC, or the full SAE J2601 station loop. Those claims still require de-identified synchronized station traces from CARB, JRC GasTeF, Cal State LA, or another independent provider.

## Reproducibility plan

Before using the dataset in a confirmatory result, freeze a parser and protocol that specify workbook, sheet, release diameter/rate, ventilation case, concentration units, spatial coordinate convention, interpolation rule, error metric, and pass thresholds. Store only derived summaries and source hashes in the repository. Keep the original files under the ignored public-validation data directory.

This record therefore improves the independent consequence-validation coverage without changing the current conclusion that the IJHE full-loop gate remains open.
