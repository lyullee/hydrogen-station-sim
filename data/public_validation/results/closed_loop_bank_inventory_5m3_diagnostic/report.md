# SAE J2601 public-data closed-loop comparison

Generated: 2026-10-08T09:41:34.518341+00:00
Source commit: `471f94b28b6ed5fae80b4e470264d2f13a050940`
Source worktree dirty: `False`
Cases: 11

> This run uses global parameters selected on separate development cases. It is an internal confirmation/iteration result, not a pristine external holdout, SAE certification, or field-safety validation.

## Model configuration

- Tank fit source: `data\public_validation\results\tank_model\validation.json`
- Tank fit: `{"effective_volume_multiplier": 1.052729261198358, "gas_liner_ua_multiplier": 31.460656519273492}`
- Dispenser flow-area multiplier: `2.0`
- Flow calibration source: `data\public_validation\results\closed_loop_flow_calibration\calibration.json`
- Precooler duty multiplier: `16.0`
- Thermal calibration source: `data\public_validation\results\closed_loop_thermal_calibration_v2\calibration.json`
- Vehicle geometry basis: `capacity_eos`
- Vehicle thermal model: `constant_ua`
- Equivalent capsule aspect ratio: `None`
- Inlet nozzle diameter: `None` m
- Cascade-bank gas volumes (low/medium/high): `[5.0, 5.0, 5.0]` m³
- Selected laboratory tests: `[3, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36]`

## Aggregate agreement

| Metric | Mean | Median | SD | Bootstrap 95% CI of mean |
|---|---:|---:|---:|---:|
| pressure_rmse_mpa | 4.357 | 4.096 | 2.370 | 3.163–5.787 |
| pressure_mae_mpa | 3.207 | 2.992 | 1.847 | 2.312–4.346 |
| temperature_rmse_c | 8.175 | 7.315 | 3.409 | 6.430–10.273 |
| temperature_mae_c | 7.030 | 6.111 | 3.111 | 5.457–8.974 |
| soc_rmse_percentage_points | 4.348 | 3.771 | 2.155 | 3.201–5.607 |

Engineering-screening pass: 6/11 (54.5%).
The screening limits are project criteria and are not an SAE acceptance rule: pressure RMSE ≤ 5.0 MPa, temperature RMSE ≤ 10.0 °C, and absolute final-SOC error ≤ 5.0 percentage points.
Final stop reasons: vehicle-target=6, gas-temperature-limit=4, none=1.

## Condition strata

| Variable | Value | Cases | P RMSE mean | T RMSE mean | SOC RMSE mean |
|---|---:|---:|---:|---:|---:|
| Tank capacity (kg) | 4.6 | 1 | 2.33 | 15.71 | 1.80 |
| Tank capacity (kg) | 4.7 | 7 | 5.04 | 8.39 | 4.93 |
| Tank capacity (kg) | 5.9 | 1 | 1.22 | 5.22 | 2.27 |
| Tank capacity (kg) | 9.8 | 2 | 4.54 | 5.12 | 4.64 |
| Chamber temperature (°C) | 0 | 2 | 3.87 | 6.43 | 3.63 |
| Chamber temperature (°C) | 20 | 5 | 5.42 | 7.75 | 5.17 |
| Chamber temperature (°C) | 40 | 3 | 3.16 | 10.99 | 3.64 |
| Chamber temperature (°C) | 50 | 1 | 3.59 | 5.33 | 3.79 |
| Scheduled APRR (MPa/min) | 6.4 | 1 | 1.22 | 5.22 | 2.27 |
| Scheduled APRR (MPa/min) | 7.6 | 1 | 3.59 | 5.33 | 3.79 |
| Scheduled APRR (MPa/min) | 11.5 | 2 | 4.13 | 13.88 | 4.32 |
| Scheduled APRR (MPa/min) | 18 | 2 | 3.72 | 7.31 | 4.47 |
| Scheduled APRR (MPa/min) | 19.4 | 1 | 5.49 | 4.92 | 5.49 |
| Scheduled APRR (MPa/min) | 21.8 | 2 | 7.09 | 9.61 | 5.72 |
| Scheduled APRR (MPa/min) | 28.5 | 1 | 3.03 | 5.55 | 3.49 |
| Scheduled APRR (MPa/min) | 35 | 1 | 4.71 | 7.32 | 3.77 |

## Per-test results

| Case | Tank | Chamber | APRR | P RMSE | T RMSE | SOC RMSE | Final SOC error | Screen |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H2P-L03 | 4.7 kg | 20.0 °C | 18.0 MPa/min | 2.67 MPa | 7.51 °C | 2.29%p | -2.78%p | PASS |
| H2P-L09 | 4.7 kg | 0.0 °C | 35.0 MPa/min | 4.71 MPa | 7.32 °C | 3.77%p | -1.96%p | PASS |
| H2P-L12 | 9.8 kg | 20.0 °C | 19.4 MPa/min | 5.49 MPa | 4.92 °C | 5.49%p | -0.47%p | FAIL |
| H2P-L15 | 4.7 kg | 40.0 °C | 11.5 MPa/min | 5.93 MPa | 12.05 °C | 6.84%p | -20.32%p | FAIL |
| H2P-L18 | 4.7 kg | 0.0 °C | 28.5 MPa/min | 3.03 MPa | 5.55 °C | 3.49%p | -1.14%p | PASS |
| H2P-L21 | 5.9 kg | 40.0 °C | 6.4 MPa/min | 1.22 MPa | 5.22 °C | 2.27%p | -3.35%p | PASS |
| H2P-L24 | 4.7 kg | 20.0 °C | 21.8 MPa/min | 4.10 MPa | 8.26 °C | 3.13%p | -2.99%p | PASS |
| H2P-L27 | 4.7 kg | 20.0 °C | 21.8 MPa/min | 10.09 MPa | 10.96 °C | 8.31%p | -4.29%p | FAIL |
| H2P-L30 | 4.6 kg | 40.0 °C | 11.5 MPa/min | 2.33 MPa | 15.71 °C | 1.80%p | -4.53%p | FAIL |
| H2P-L33 | 9.8 kg | 50.0 °C | 7.6 MPa/min | 3.59 MPa | 5.33 °C | 3.79%p | -11.34%p | FAIL |
| H2P-L36 | 4.7 kg | 20.0 °C | 18.0 MPa/min | 4.77 MPa | 7.11 °C | 6.66%p | -2.43%p | PASS |

## Boundary assumptions

- Initial pressure and gas temperature, chamber temperature, scheduled APRR, median inlet-gas temperature, and final comparison time come from each experiment.
- Maximum flow remains fixed at the 60 g/s model setting; observed peak flow is not fitted.
- Vessel gas volume is calculated from declared capacity and hydrogen EOS density at nominal pressure and 15 °C.
- The constant-UA tank model does not require an assumed vessel aspect ratio.
- Cascade-bank volumes are declared model inputs. Public J2601 case files do not identify the station-side storage inventory, so a changed value is a source-boundary sensitivity and not a reconstructed test-rig measurement.
- Predictions are interpolated to the experimental clock without dynamic time warping.
