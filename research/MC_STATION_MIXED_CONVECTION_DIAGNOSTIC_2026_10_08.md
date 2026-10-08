# MC Default full-station mixed-convection diagnostic

> Post-outcome development diagnostic only. The frozen external result remains 0/8.

The full station runtime was evaluated with a volume-preserving equivalent Type-IV tank and a declared 3/5/7 mm inlet-nozzle range. The source archive does not disclose the physical vessel pack or nozzle geometry, so no row is selected as the production model.

| Thermal model | Nozzle | Joint screens | P RMSE | T RMSE | SOC RMSE | Temperature stops |
|---|---:|---:|---:|---:|---:|---:|
| constant_ua | n/a | 0/8 | 30.81 MPa | 14.98 °C | 37.16%p | 7 |
| mixed_convection | 3 mm | 0/8 | 11.78 MPa | 12.37 °C | 13.34%p | 5 |
| mixed_convection | 5 mm | 0/8 | 11.83 MPa | 12.34 °C | 13.40%p | 5 |
| mixed_convection | 7 mm | 0/8 | 11.87 MPa | 12.32 °C | 13.44%p | 5 |

## Result

Mixed convection materially improves the matched uncalibrated-UA comparator, but it leaves five premature temperature stops and zero joint screening passes at every declared nozzle diameter. No diameter or production default is selected.

## Interpretation boundary

These outcomes were already inspected. This sensitivity cannot revise the frozen 0/8 external holdout, identify the undisclosed physical vessel or nozzle geometry, select a production configuration, validate the complete station, or close an IJHE gate.

The geometry is a single lumped equivalent used to expose model-form sensitivity. It is not a reconstruction of a multi-cylinder vehicle storage system.
