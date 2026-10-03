# NREL H2FillS geometry sensitivity

This is an exploratory diagnostic for the independent NREL HDVS Type-IV
workbook. It is not a confirmatory validation result and does not change the
frozen model or any published claim.

## Reproduction

```text
PYTHONPATH=src python scripts/run_nrel_h2fills_geometry_sensitivity.py
```

The runner is `scripts/run_nrel_h2fills_geometry_sensitivity.py` (SHA-256
`28ff53a29b234ad8ac1a84e940ed80edbd5f02cc36c627465513ef811c8e34b3`). The raw
workbook remains local and ignored because the H2FillS package licence does not
grant redistribution. Its SHA-256 is
`1a3fbe64a50c1c97266bfe0372998513ad3ccec5600fab7bc4b9fc68ad4d9d0c`.

The capacity/EOS volume is computed from the declared 9.8 kg tank capacity and
tabulated hydrogen density at 70 MPa and 15 °C:

```text
V = 9.8 kg / rho_H2(70 MPa, 288.15 K) = 0.2439432 m³
```

No measured NREL pressure or temperature value is used to identify this volume.

## Exploratory screen

| Variant | Base volume | Effective-volume multiplier | Pressure RMSE | Temperature RMSE | Final mass error | Tanks passing |
|---|---:|---:|---:|---:|---:|---:|
| Legacy frozen | 0.254383 m³ | 1.052729 | 6.164 MPa | 4.625 °C | 0.120 kg | 0/7 |
| Capacity/EOS with frozen fit | 0.243943 m³ | 1.052729 | 3.538 MPa | 4.255 °C | 0.102 kg | 7/7 |
| Capacity/EOS, no volume fit | 0.243943 m³ | 1.000000 | 0.496 MPa | 4.185 °C | 0.080 kg | 7/7 |

The result is a strong structural diagnostic: the legacy volume assumption is
larger than the EOS-equivalent volume implied by the independent workbook and
causes a systematic pressure under-prediction. It is not evidence that the
capacity/EOS variant is already validated, because the variants were selected
and compared after the external workbook had been opened.

## Required confirmatory procedure

Before using a capacity/EOS geometry in a paper claim, freeze the geometry rule,
fit parameters, source commit, split and scoring metrics. Re-run the existing
H2Protocol calibration/holdout without changing the holdout, then evaluate the
frozen result on a second untouched external dataset with synchronized station
and vehicle channels. Preserve this report as exploratory evidence and retain
the current default until that protocol is complete.
