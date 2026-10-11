# Cross-dataset capacity/EOS geometry transfer matrix

This is a post-outcome development synthesis. It does not promote a
validation gate or change the runtime geometry rule.

| Dataset | Variant | Effective-volume multiplier | Joint pass | Cases |
|---|---|---:|---:|---:|
| Powertech MC Default vehicle-tank boundary | frozen_tables_method_effective_volume | 1.051988 | 0 | 8 |
| Powertech MC Default vehicle-tank boundary | unadjusted_reference_volume | 1.000000 | 4 | 8 |
| Powertech MC Default vehicle-tank boundary | capacity_eos_volume | 0.958960 | 4 | 8 |
| NREL H2FillS HDVS Type-IV tank boundary | legacy_frozen | 1.052729 | 0 | 7 |
| NREL H2FillS HDVS Type-IV tank boundary | capacity_eos_with_frozen_fit | 1.052729 | 7 | 7 |
| NREL H2FillS HDVS Type-IV tank boundary | capacity_eos_no_volume_fit | 1.000000 | 7 | 7 |

## Findings

- The globally fitted tables-method multiplier does not transfer to the MC Default vessel set: 0/8 joint screens remained after the frozen rule, while two non-fitted geometry rules reached only 4/8.
- The NREL post-access sample is highly sensitive to the declared capacity/EOS geometry basis: both capacity-EOS variants reached 7/7, while the legacy nominal-volume rule reached 0/7.
- No single post-outcome variant may be selected as a universal production rule. The evidence supports requiring source-declared internal volume or a predeclared capacity/EOS rule before a new untouched holdout.

## Required next evidence

- At least one new untouched tank-and-hose cohort with declared capacity, internal volume or traceable geometry, inlet pressure/temperature, common time base and transferred mass.
- Freeze the geometry rule and screening limits before numeric outcomes are opened.
- Retain all cases and do not promote a post-outcome sensitivity to the validation gate.

This matrix explains geometry-transfer risk and preserves negative evidence. It is not an external validation result, does not revise the frozen MC or NREL outcomes, does not select a runtime default and cannot establish station, vehicle-controller or field-safety validity.
