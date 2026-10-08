# Closed-loop mixed-convection diagnostic

> Post-outcome model-development evidence only. The frozen external holdout remains unchanged.

A single declared 3 mm inlet nozzle and a volume-preserving capsule surrogate with cylindrical length/diameter 5 were applied to the same 11 already-inspected comparison fills. No result-dependent geometry or parameter was selected.

| Model | Joint screens | Pressure RMSE | Temperature RMSE | SOC RMSE |
|---|---:|---:|---:|---:|
| Constant UA baseline | 2/11 | 4.530 MPa | 7.819 °C | 4.625%p |
| Mixed convection | 2/11 | 4.311 MPa | 7.156 °C | 4.380%p |

## Decision

Retain constant-UA as the production default. Mixed convection modestly reduced all three aggregate mean errors but did not increase the joint screen pass count; controller and boundary-model error remains material.

The mean errors fell by 4.8% for pressure_rmse_mpa, 8.5% for temperature_rmse_c, 5.3% for soc_rmse_percentage_points, but the strict joint-screen count did not change. The heat-transfer path remains opt-in research functionality.

## Boundary

The 11 outcomes were already inspected before this model-form comparison. The result cannot revise the frozen 0/8 MC Default holdout, identify the undisclosed physical tank/nozzle geometry, establish SAE conformance, validate field safety, or close an IJHE external-validation gate.
