# Prospective Dickens Type-III tank validation

## Decision

The frozen, unfitted layered tank model **failed** the joint external-validation
rule. It passed both pressure screens but failed both gas-temperature screens.
The result is retained as a negative result and does not validate the HRS loop or
change the production runtime.

| Frozen primary metric | Result | Limit | Decision |
|---|---:|---:|---|
| Pressure RMSE | 0.943 MPa | <= 2 MPa | PASS |
| Pressure NRMSE / measured span | 3.742% | <= 5% | PASS |
| Mean-gas-temperature RMSE | 19.179 K | <= 10 K | FAIL |
| Peak-temperature absolute error | 18.720 K | <= 15 K | FAIL |

Relative mass and energy residuals were (4.49\times10^{-16}) and
(1.37\times10^{-15}), respectively. The failure is therefore a physical-model
limitation rather than a conservation or integration failure.

## Evidence design

The protocol was frozen before numerical measurement values were printed or
reviewed. It fixes the public archive and case hashes, source geometry and
materials, measured mass-flow boundary, inlet-enthalpy rule, natural-convection
correlation, tolerances and acceptance screens. No parameter was fitted. The
repository stores only aggregate errors and source hashes; it does not republish
the source measurement arrays.

- Dataset DOI: `10.5281/zenodo.20728325`
- Frozen protocol: `research/dickens_typeiii_prospective_protocol_2026_10_08.json`
- Frozen result: `research/dickens_typeiii_prospective_result_2026_10_08.json`
- Runner: `scripts/run_dickens_typeiii_prospective.py`

## Post-outcome mechanism check

After the failure was known, an optional inlet-jet forced-convection term was
implemented. The existing constant-UA runtime remains the default. An unfitted
3, 5 and 7 mm inlet-diameter sensitivity reduced temperature RMSE to
7.215--7.915 K and pressure RMSE to 0.653--0.674 MPa; all four screens passed for
all three sensitivity cases. This strongly identifies omitted inlet-jet mixing
as the leading thermal mechanism, but it is **not confirmatory validation**:
the experiment's exact nozzle diameter and time-resolved inlet temperature are
not available, and the diagnostic was designed after inspecting the failed
outcome.

- Diagnostic: `research/dickens_typeiii_mixed_convection_diagnostic_2026_10_08.json`
- Diagnostic runner: `scripts/run_dickens_typeiii_mixed_convection_diagnostic.py`
- Runtime parameter updated: **no**
- Frozen validation decision changed: **no**

The physical mechanism is consistent with Couteau et al.'s open-access finding
that a turbulent inlet jet creates a mixing zone during high-pressure hydrogen
filling ([DOI 10.1016/j.ijhydene.2025.04.015](https://doi.org/10.1016/j.ijhydene.2025.04.015)).
The public [HyTF reference implementation](https://github.com/ArtCouteau/HyTF)
was inspected at commit `f0e8f0446fe7638abe21734d14e654a8a79f95fc` under
GPL-3.0. No source code was copied into this MIT project; the correlation was
expressed independently and HyTF's separate fitted factor of two was omitted.

## Next decisive experiment

Freeze the mixed-convection formulation and exact inlet geometry before opening
a new filling trace. The holdout must provide tank volume and internal diameter,
inlet/nozzle diameter, time-resolved mass flow and inlet temperature, tank
pressure, spatial or mean gas temperature, ambient condition and sensor
locations. A fresh joint pass can support transfer of the tank-filling submodel;
it still cannot validate cascade control, compressor or precooler behavior,
dispenser metering, consequence distance, safety logic or SAGA effectiveness.
