# SAE J2601 public-data closed-loop comparison

Generated: 2026-10-03T03:43:02.722774+00:00
Source commit: `f7a99b7361b4e8685c1254b747cd4d848ef22e03`
Source worktree dirty: `False`
Cases: 11

> This run uses global parameters selected on separate development cases. It is an internal confirmation/iteration result, not a pristine external holdout, SAE certification, or field-safety validation.

## Model configuration

- Tank fit source: `data\public_validation\results\tank_model\validation.json`
- Tank fit: `{"effective_volume_multiplier": 1.0519881596076546, "gas_liner_ua_multiplier": 64.43011313151457}`
- Dispenser flow-area multiplier: `1.25`
- Flow calibration source: `data\public_validation\results\closed_loop_flow_calibration\calibration.json`
- Precooler duty multiplier: `8.0`
- Thermal calibration source: `data\public_validation\results\closed_loop_thermal_calibration\calibration.json`
- Selected laboratory tests: `[3, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36]`

## Aggregate agreement

| Metric | Mean | Median | SD | Bootstrap 95% CI of mean |
|---|---:|---:|---:|---:|
| pressure_rmse_mpa | 6.790 | 6.961 | 2.738 | 5.208–8.263 |
| pressure_mae_mpa | 5.377 | 5.094 | 2.326 | 4.039–6.648 |
| temperature_rmse_c | 8.570 | 8.477 | 3.123 | 6.971–10.468 |
| temperature_mae_c | 7.505 | 7.209 | 2.822 | 6.039–9.213 |
| soc_rmse_percentage_points | 9.540 | 8.520 | 5.095 | 7.087–12.713 |

Engineering-screening pass: 0/11 (0.0%).
The screening limits are project criteria and are not an SAE acceptance rule: pressure RMSE ≤ 5.0 MPa, temperature RMSE ≤ 10.0 °C, and absolute final-SOC error ≤ 5.0 percentage points.
Final stop reasons: none=8, safety-temperature=1, vehicle-target=2.

## Condition strata

| Variable | Value | Cases | P RMSE mean | T RMSE mean | SOC RMSE mean |
|---|---:|---:|---:|---:|---:|
| Tank capacity (kg) | 4.6 | 1 | 4.11 | 14.96 | 4.80 |
| Tank capacity (kg) | 4.7 | 7 | 7.29 | 8.40 | 8.18 |
| Tank capacity (kg) | 5.9 | 1 | 1.32 | 6.26 | 22.75 |
| Tank capacity (kg) | 9.8 | 2 | 9.13 | 7.14 | 10.08 |
| Chamber temperature (°C) | 0 | 2 | 8.52 | 5.44 | 9.14 |
| Chamber temperature (°C) | 20 | 5 | 7.53 | 8.63 | 8.50 |
| Chamber temperature (°C) | 40 | 3 | 4.13 | 11.50 | 11.89 |
| Chamber temperature (°C) | 50 | 1 | 7.61 | 5.75 | 8.52 |
| Scheduled APRR (MPa/min) | 6.4 | 1 | 1.32 | 6.26 | 22.75 |
| Scheduled APRR (MPa/min) | 7.6 | 1 | 7.61 | 5.75 | 8.52 |
| Scheduled APRR (MPa/min) | 11.5 | 2 | 5.53 | 14.12 | 6.45 |
| Scheduled APRR (MPa/min) | 18 | 2 | 7.31 | 8.19 | 9.42 |
| Scheduled APRR (MPa/min) | 19.4 | 1 | 10.65 | 8.53 | 11.63 |
| Scheduled APRR (MPa/min) | 21.8 | 2 | 6.19 | 9.12 | 6.00 |
| Scheduled APRR (MPa/min) | 28.5 | 1 | 8.14 | 5.10 | 8.56 |
| Scheduled APRR (MPa/min) | 35 | 1 | 8.89 | 5.78 | 9.72 |

## Per-test results

| Case | Tank | Chamber | APRR | P RMSE | T RMSE | SOC RMSE | Final SOC error | Screen |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H2P-L03 | 4.7 kg | 20.0 °C | 18.0 MPa/min | 4.66 MPa | 8.48 °C | 5.63%p | -7.43%p | FAIL |
| H2P-L09 | 4.7 kg | 0.0 °C | 35.0 MPa/min | 8.89 MPa | 5.78 °C | 9.72%p | -5.55%p | FAIL |
| H2P-L12 | 9.8 kg | 20.0 °C | 19.4 MPa/min | 10.65 MPa | 8.53 °C | 11.63%p | -6.82%p | FAIL |
| H2P-L15 | 4.7 kg | 40.0 °C | 11.5 MPa/min | 6.96 MPa | 13.28 °C | 8.11%p | -20.91%p | FAIL |
| H2P-L18 | 4.7 kg | 0.0 °C | 28.5 MPa/min | 8.14 MPa | 5.10 °C | 8.56%p | -4.96%p | FAIL |
| H2P-L21 | 5.9 kg | 40.0 °C | 6.4 MPa/min | 1.32 MPa | 6.26 °C | 22.75%p | -41.25%p | FAIL |
| H2P-L24 | 4.7 kg | 20.0 °C | 21.8 MPa/min | 5.63 MPa | 8.71 °C | 6.38%p | -6.90%p | FAIL |
| H2P-L27 | 4.7 kg | 20.0 °C | 21.8 MPa/min | 6.76 MPa | 9.53 °C | 5.62%p | -7.37%p | FAIL |
| H2P-L30 | 4.6 kg | 40.0 °C | 11.5 MPa/min | 4.11 MPa | 14.96 °C | 4.80%p | -4.56%p | FAIL |
| H2P-L33 | 9.8 kg | 50.0 °C | 7.6 MPa/min | 7.61 MPa | 5.75 °C | 8.52%p | -16.41%p | FAIL |
| H2P-L36 | 4.7 kg | 20.0 °C | 18.0 MPa/min | 9.96 MPa | 7.90 °C | 13.21%p | -2.84%p | FAIL |

## Boundary assumptions

- Initial pressure and gas temperature, chamber temperature, scheduled APRR, median inlet-gas temperature, and final comparison time come from each experiment.
- Maximum flow remains fixed at the 60 g/s model setting; observed peak flow is not fitted.
- Vessel volume is scaled from the demonstrator's 0.122 m³ per 4.7 kg surrogate because the public overview does not provide machine-readable vessel geometry.
- Predictions are interpolated to the experimental clock without dynamic time warping.
