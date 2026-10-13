# MC temperature sensor-envelope diagnostic

This post-outcome development diagnostic compares predefined tank states with the simultaneous range of the public in-tank thermocouples. It does not select an observation operator or change runtime parameters.

## Aggregate result

| State | Mean-trace RMSE | Sensor-envelope RMSE | Inside envelope | Cases ≤ 10 °C |
|---|---:|---:|---:|---:|
| gas_temperature | 9.202 °C | 8.593 °C | 7.7% | 4/8 |
| liner_temperature | 9.015 °C | 8.347 °C | 8.1% | 4/8 |
| shell_temperature | 29.005 °C | 28.350 °C | 0.6% | 0/8 |
| liner_shell_mean | 14.285 °C | 13.632 °C | 8.9% | 2/8 |

## Interpretation

The sensor envelope distinguishes spatial thermocouple spread from model-state error without choosing a favorable observation operator. A low envelope error would support a sensor-location explanation; a large error for all states would retain the heat-transfer-model limitation.

## Claim boundary

This is a privacy-safe, post-outcome sensor-envelope diagnostic. It cannot select a temperature observation operator, calibrate heat transfer, change runtime behavior, close an external-validation gate, or support a vehicle or field-safety claim.
