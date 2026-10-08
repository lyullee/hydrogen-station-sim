# SAE J2601 public-data closed-loop comparison

Generated: 2026-10-08T09:16:18.732548+00:00
Source commit: `ffebf256fa2316d5f691cca00c005279b25706ff`
Source worktree dirty: `True`
Cases: 11

> This run uses global parameters selected on separate development cases. It is an internal confirmation/iteration result, not a pristine external holdout, SAE certification, or field-safety validation.

## Model configuration

- Tank fit source: `none`
- Tank fit: `null`
- Dispenser flow-area multiplier: `2.0`
- Flow calibration source: `data\public_validation\results\closed_loop_flow_calibration\calibration.json`
- Precooler duty multiplier: `16.0`
- Thermal calibration source: `data\public_validation\results\closed_loop_thermal_calibration_v2\calibration.json`
- Vehicle geometry basis: `capacity_eos`
- Vehicle thermal model: `mixed_convection`
- Equivalent capsule aspect ratio: `5.0`
- Inlet nozzle diameter: `0.003` m
- Selected laboratory tests: `[3, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36]`

## Aggregate agreement

| Metric | Mean | Median | SD | Bootstrap 95% CI of mean |
|---|---:|---:|---:|---:|
| pressure_rmse_mpa | 4.311 | 4.548 | 2.082 | 3.233–5.574 |
| pressure_mae_mpa | 3.131 | 3.029 | 1.561 | 2.349–4.081 |
| temperature_rmse_c | 7.156 | 6.748 | 3.446 | 5.419–9.293 |
| temperature_mae_c | 6.163 | 5.757 | 3.136 | 4.573–8.118 |
| soc_rmse_percentage_points | 4.380 | 4.216 | 2.050 | 3.284–5.579 |

Engineering-screening pass: 2/11 (18.2%).
The screening limits are project criteria and are not an SAE acceptance rule: pressure RMSE ≤ 5.0 MPa, temperature RMSE ≤ 10.0 °C, and absolute final-SOC error ≤ 5.0 percentage points.
Final stop reasons: none=8, gas-temperature-limit=1, vehicle-target=2.

## Condition strata

| Variable | Value | Cases | P RMSE mean | T RMSE mean | SOC RMSE mean |
|---|---:|---:|---:|---:|---:|
| Tank capacity (kg) | 4.6 | 1 | 2.72 | 14.35 | 1.51 |
| Tank capacity (kg) | 4.7 | 7 | 4.73 | 6.94 | 4.90 |
| Tank capacity (kg) | 5.9 | 1 | 1.41 | 5.47 | 2.43 |
| Tank capacity (kg) | 9.8 | 2 | 5.08 | 5.17 | 4.96 |
| Chamber temperature (°C) | 0 | 2 | 3.92 | 3.60 | 3.81 |
| Chamber temperature (°C) | 20 | 5 | 4.98 | 6.85 | 5.11 |
| Chamber temperature (°C) | 40 | 3 | 3.02 | 10.78 | 3.21 |
| Chamber temperature (°C) | 50 | 1 | 5.61 | 4.93 | 5.42 |
| Scheduled APRR (MPa/min) | 6.4 | 1 | 1.41 | 5.47 | 2.43 |
| Scheduled APRR (MPa/min) | 7.6 | 1 | 5.61 | 4.93 | 5.42 |
| Scheduled APRR (MPa/min) | 11.5 | 2 | 3.82 | 13.43 | 3.59 |
| Scheduled APRR (MPa/min) | 18 | 2 | 4.16 | 7.02 | 4.95 |
| Scheduled APRR (MPa/min) | 19.4 | 1 | 4.55 | 5.41 | 4.49 |
| Scheduled APRR (MPa/min) | 21.8 | 2 | 6.02 | 7.40 | 5.58 |
| Scheduled APRR (MPa/min) | 28.5 | 1 | 3.08 | 2.87 | 3.39 |
| Scheduled APRR (MPa/min) | 35 | 1 | 4.76 | 4.33 | 4.22 |

## Per-test results

| Case | Tank | Chamber | APRR | P RMSE | T RMSE | SOC RMSE | Final SOC error | Screen |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H2P-L03 | 4.7 kg | 20.0 °C | 18.0 MPa/min | 2.98 MPa | 6.96 °C | 2.86%p | -7.27%p | FAIL |
| H2P-L09 | 4.7 kg | 0.0 °C | 35.0 MPa/min | 4.76 MPa | 4.33 °C | 4.22%p | -5.28%p | FAIL |
| H2P-L12 | 9.8 kg | 20.0 °C | 19.4 MPa/min | 4.55 MPa | 5.41 °C | 4.49%p | -5.58%p | FAIL |
| H2P-L15 | 4.7 kg | 40.0 °C | 11.5 MPa/min | 4.93 MPa | 12.51 °C | 5.67%p | -17.61%p | FAIL |
| H2P-L18 | 4.7 kg | 0.0 °C | 28.5 MPa/min | 3.08 MPa | 2.87 °C | 3.39%p | -4.56%p | PASS |
| H2P-L21 | 5.9 kg | 40.0 °C | 6.4 MPa/min | 1.41 MPa | 5.47 °C | 2.43%p | -2.00%p | PASS |
| H2P-L24 | 4.7 kg | 20.0 °C | 21.8 MPa/min | 2.87 MPa | 6.75 °C | 2.93%p | -6.60%p | FAIL |
| H2P-L27 | 4.7 kg | 20.0 °C | 21.8 MPa/min | 9.18 MPa | 8.05 °C | 8.23%p | -7.18%p | FAIL |
| H2P-L30 | 4.6 kg | 40.0 °C | 11.5 MPa/min | 2.72 MPa | 14.35 °C | 1.51%p | -4.56%p | FAIL |
| H2P-L33 | 9.8 kg | 50.0 °C | 7.6 MPa/min | 5.61 MPa | 4.93 °C | 5.42%p | -15.31%p | FAIL |
| H2P-L36 | 4.7 kg | 20.0 °C | 18.0 MPa/min | 5.34 MPa | 7.08 °C | 7.03%p | -2.46%p | FAIL |

## Boundary assumptions

- Initial pressure and gas temperature, chamber temperature, scheduled APRR, median inlet-gas temperature, and final comparison time come from each experiment.
- Maximum flow remains fixed at the 60 g/s model setting; observed peak flow is not fitted.
- Vessel gas volume is calculated from declared capacity and hydrogen EOS density at nominal pressure and 15 °C.
- Mixed convection uses a volume-preserving capsule surrogate with the declared aspect ratio and nozzle diameter. It is a model-form diagnostic, not a reconstruction of the undisclosed physical vessel pack.
- Predictions are interpolated to the experimental clock without dynamic time warping.
