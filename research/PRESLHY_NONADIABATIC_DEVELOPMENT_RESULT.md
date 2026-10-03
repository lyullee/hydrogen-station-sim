# PRESLHY non-adiabatic development result

This is a model-development result on consumed E3.1 Part A data. It is **not independent external validation** and cannot support the revised-model claim by itself.

## Result

- Eligible development cases: 22
- Both frozen screens passed: 20/22 (90.9%)
- Experiment bootstrap 95% interval: 77.3%–100.0%
- Model/integration errors: 0

All nine high-pressure cases, all seven medium-pressure cases, and four of six low-pressure cases passed. The two failures were low-pressure 0.5 mm and 1 mm tests, where pressure NRMSE passed but half-gauge-pressure timing error exceeded 20%.

## Interpretation

Adding measured wall thermal inertia and physical gas-wall/ambient heat transfer removed the six property-domain failures and raised the diagnostic joint pass fraction from 50.0% to 90.9%. This supports the failure explanation and justifies a new holdout test. It does not convert the original negative evaluation into a positive result.

## Failed development cases

- 20190523_155208, 0.5 mm, 5.776 bar abs: pressure NRMSE 4.03%, half-time error 81.72%.
- 20190523_151618, 1 mm, 6.432 bar abs: pressure NRMSE 8.03%, half-time error 71.09%.

The machine-readable record includes package hashes, implementation hashes, every case metric, and the predeclared development-evidence boundary.
