# Closed-loop cascade inventory sensitivity

**Status:** post-outcome diagnostic only; no validation gate effect.

## Fixed comparison

- Cases: 11 already-inspected Powertech H2Protocol comparison cases.
- Baseline cascade inventory: 0.35 m³ for each low/medium/high bank.
- Alternative: 5.0 m³ for each bank, tested once without a volume grid.
- All vehicle, dispenser, controller and precooler settings were unchanged.
- The alternative is a rounded hypothesis within the 2.737–8.697 m³ conditional source-volume range calculated from separate public source-pressure records.

## Result

| Metric | 0.35 m³ banks | 5.0 m³ banks | Change |
|---|---:|---:|---:|
| Engineering-screening passes | 2/11 | 6/11 | +4 cases |
| Mean pressure RMSE | 4.530 MPa | 4.357 MPa | -0.173 MPa |
| Mean temperature RMSE | 7.819 °C | 8.175 °C | +0.356 °C |
| Mean SOC RMSE | 4.625%p | 4.348%p | -0.277%p |

Pressure and SOC agreement improve while temperature agreement becomes slightly worse. The paired bootstrap 95% confidence interval for each mean change includes zero, so direction and magnitude are diagnostic rather than confirmatory.

## Claim boundary

The 5 m³ value is not an identified test-rig parameter. The public files do not disclose connected storage topology, valve states, regulator behavior or source temperature. The cases and source diagnostics had already been inspected, so this result cannot be promoted to independent external validation or used to change the production default.

Artifacts:

- Baseline: `research/closed_loop_internal_comparison_v2.json`
- Alternative: `data/public_validation/results/closed_loop_bank_inventory_5m3_diagnostic/validation.json`
- Machine-readable record: `research/closed_loop_bank_inventory_sensitivity_2026_10_08.json`
