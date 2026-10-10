# SAE J2601 public-data closed-loop comparison

Generated: 2026-10-10T04:29:03.107507+00:00
Source commit: `65b401e5551c1817f41b4a603711acb798c4120b`
Source worktree dirty: `False`
Cases: 11

> This run uses global parameters selected on separate development cases. It is an internal confirmation/iteration result, not a pristine external holdout, SAE certification, or field-safety validation.

## Model configuration

- Tank fit source: `data\public_validation\results\tank_model\validation.json`
- Tank fit: `{"effective_volume_multiplier": 1.052729261198358, "gas_liner_ua_multiplier": 31.460656519273492}`
- Dispenser flow-area multiplier: `2.0`
- Flow calibration source: `data\public_validation\results\closed_loop_flow_calibration\calibration.json`
- Precooler duty multiplier: `8.0`
- Thermal calibration source: `data\public_validation\results\closed_loop_thermal_calibration\calibration.json`
- Vehicle geometry basis: `capacity_eos`
- Vehicle thermal model: `mixed_convection`
- Equivalent capsule aspect ratio: `5.0`
- Inlet nozzle diameter: `0.003` m
- Cascade-bank gas volumes (low/medium/high): `[0.35, 0.35, 0.35]` m³
- Selected laboratory tests: `[3, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36]`

## Aggregate agreement

| Metric | Mean | Median | SD | Bootstrap 95% CI of mean |
|---|---:|---:|---:|---:|
| pressure_rmse_mpa | 4.190 | 3.693 | 2.101 | 3.098–5.461 |
| pressure_mae_mpa | 3.041 | 2.560 | 1.575 | 2.236–4.007 |
| temperature_rmse_c | 7.710 | 7.267 | 3.338 | 6.009–9.761 |
| temperature_mae_c | 6.647 | 6.267 | 3.108 | 5.070–8.559 |
| soc_rmse_percentage_points | 4.282 | 3.563 | 2.119 | 3.150–5.553 |

Engineering-screening pass: 1/11 (9.1%).
The screening limits are project criteria and are not an SAE acceptance rule: pressure RMSE ≤ 5.0 MPa, temperature RMSE ≤ 10.0 °C, and absolute final-SOC error ≤ 5.0 percentage points.
Final stop reasons: none=8, gas-temperature-limit=1, vehicle-target=2.

## Condition strata

| Variable | Value | Cases | P RMSE mean | T RMSE mean | SOC RMSE mean |
|---|---:|---:|---:|---:|---:|
| Tank capacity (kg) | 4.6 | 1 | 2.74 | 14.58 | 1.64 |
| Tank capacity (kg) | 4.7 | 7 | 4.60 | 7.39 | 4.79 |
| Tank capacity (kg) | 5.9 | 1 | 1.35 | 6.52 | 2.49 |
| Tank capacity (kg) | 9.8 | 2 | 4.89 | 5.98 | 4.73 |
| Chamber temperature (°C) | 0 | 2 | 3.43 | 4.03 | 3.29 |
| Chamber temperature (°C) | 20 | 5 | 4.84 | 7.48 | 4.98 |
| Chamber temperature (°C) | 40 | 3 | 2.99 | 11.33 | 3.25 |
| Chamber temperature (°C) | 50 | 1 | 6.09 | 5.36 | 5.89 |
| Scheduled APRR (MPa/min) | 6.4 | 1 | 1.35 | 6.52 | 2.49 |
| Scheduled APRR (MPa/min) | 7.6 | 1 | 6.09 | 5.36 | 5.89 |
| Scheduled APRR (MPa/min) | 11.5 | 2 | 3.81 | 13.73 | 3.62 |
| Scheduled APRR (MPa/min) | 18 | 2 | 4.39 | 7.59 | 5.22 |
| Scheduled APRR (MPa/min) | 19.4 | 1 | 3.69 | 6.60 | 3.56 |
| Scheduled APRR (MPa/min) | 21.8 | 2 | 5.86 | 7.82 | 5.44 |
| Scheduled APRR (MPa/min) | 28.5 | 1 | 2.65 | 3.15 | 2.90 |
| Scheduled APRR (MPa/min) | 35 | 1 | 4.22 | 4.91 | 3.68 |

## Per-test results

| Case | Tank | Chamber | APRR | P RMSE | T RMSE | SOC RMSE | Final SOC error | Screen |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H2P-L03 | 4.7 kg | 20.0 °C | 18.0 MPa/min | 3.03 MPa | 7.50 °C | 2.90%p | -7.77%p | FAIL |
| H2P-L09 | 4.7 kg | 0.0 °C | 35.0 MPa/min | 4.22 MPa | 4.91 °C | 3.68%p | -5.91%p | FAIL |
| H2P-L12 | 9.8 kg | 20.0 °C | 19.4 MPa/min | 3.69 MPa | 6.60 °C | 3.56%p | -6.47%p | FAIL |
| H2P-L15 | 4.7 kg | 40.0 °C | 11.5 MPa/min | 4.88 MPa | 12.88 °C | 5.60%p | -17.38%p | FAIL |
| H2P-L18 | 4.7 kg | 0.0 °C | 28.5 MPa/min | 2.65 MPa | 3.15 °C | 2.90%p | -5.03%p | FAIL |
| H2P-L21 | 5.9 kg | 40.0 °C | 6.4 MPa/min | 1.35 MPa | 6.52 °C | 2.49%p | -1.96%p | PASS |
| H2P-L24 | 4.7 kg | 20.0 °C | 21.8 MPa/min | 2.86 MPa | 7.27 °C | 2.95%p | -7.10%p | FAIL |
| H2P-L27 | 4.7 kg | 20.0 °C | 21.8 MPa/min | 8.85 MPa | 8.36 °C | 7.92%p | -7.65%p | FAIL |
| H2P-L30 | 4.6 kg | 40.0 °C | 11.5 MPa/min | 2.74 MPa | 14.58 °C | 1.64%p | -5.04%p | FAIL |
| H2P-L33 | 9.8 kg | 50.0 °C | 7.6 MPa/min | 6.09 MPa | 5.36 °C | 5.89%p | -16.12%p | FAIL |
| H2P-L36 | 4.7 kg | 20.0 °C | 18.0 MPa/min | 5.74 MPa | 7.67 °C | 7.55%p | -2.55%p | FAIL |

## Boundary assumptions

- Initial pressure and gas temperature, chamber temperature, scheduled APRR, median inlet-gas temperature, and final comparison time come from each experiment.
- Maximum flow remains fixed at the 60 g/s model setting; observed peak flow is not fitted.
- Vessel gas volume is calculated from declared capacity and hydrogen EOS density at nominal pressure and 15 °C.
- Mixed convection uses a volume-preserving capsule surrogate with the declared aspect ratio and nozzle diameter. It is a model-form diagnostic, not a reconstruction of the undisclosed physical vessel pack.
- Cascade-bank volumes are declared model inputs. Public J2601 case files do not identify the station-side storage inventory, so a changed value is a source-boundary sensitivity and not a reconstructed test-rig measurement.
- Predictions are interpolated to the experimental clock without dynamic time warping.
