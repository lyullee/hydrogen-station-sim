# PRESLHY ambient blowdown external validation

- Decision: **PASS**
- Eligible cases: **22**; excluded: **0**
- Joint primary pass fraction: **72.7%** (case-bootstrap 95% CI 54.5%–90.9%)
- Predeclared threshold: **70%**
- Evaluation errors retained as failures: **0**
- Protocol SHA-256: `d40cc59af3a607e66870d2afb91014058c83ae96fc1ba4aeac0d8554953733af`
- Runner commit: `d5767d6a08d86f3322cdd572e84be36d82a3db18`

The frozen ambient direct-aperture source-depletion model met the predeclared external-validation decision rule.

## Stratified result

| Stratum | Cases | Pressure pass | Half-time pass | Joint pass | Errors |
|---|---:|---:|---:|---:|---:|
| by_nozzle_diameter_mm: 0.5 | 4 | 4 | 3 | 3 | 0 |
| by_nozzle_diameter_mm: 1.0 | 4 | 3 | 0 | 0 | 0 |
| by_nozzle_diameter_mm: 2.0 | 7 | 6 | 7 | 6 | 0 |
| by_nozzle_diameter_mm: 4.0 | 7 | 7 | 7 | 7 | 0 |
| by_initial_pressure_group: high | 9 | 9 | 7 | 7 | 0 |
| by_initial_pressure_group: low | 6 | 4 | 4 | 3 | 0 |
| by_initial_pressure_group: medium | 7 | 7 | 6 | 6 | 0 |

## Case-level result

| Case | d (mm) | P0 (bar abs) | Group | P NRMSE (%) | t50 error (%) | Joint | Error |
|---|---:|---:|---|---:|---:|---|---|
| 20190523_152309 | 0.5 | 201.945 | high | 2.877 | 6.400 | PASS |  |
| 20190523_153415 | 0.5 | 101.377 | high | 3.439 | 7.783 | PASS |  |
| 20190523_154414 | 0.5 | 21.523 | medium | 5.984 | 9.544 | PASS |  |
| 20190523_155208 | 0.5 | 5.776 | low | 9.947 | 46.931 | FAIL |  |
| 20190523_144939 | 1 | 201.750 | high | 5.437 | 20.054 | FAIL |  |
| 20190523_150133 | 1 | 102.577 | high | 6.457 | 21.049 | FAIL |  |
| 20190523_151013 | 1 | 21.564 | medium | 9.903 | 20.582 | FAIL |  |
| 20190523_151618 | 1 | 6.432 | low | 12.457 | 56.410 | FAIL |  |
| 20190523_143501 | 2 | 50.719 | medium | 3.164 | 5.042 | PASS |  |
| 20190523_143801 | 2 | 23.123 | medium | 4.276 | 5.088 | PASS |  |
| 20190523_144022 | 2 | 10.967 | low | 6.646 | 0.480 | PASS |  |
| 20190523_144219 | 2 | 5.766 | low | 10.620 | 14.979 | FAIL |  |
| 20190624_151045 | 2 | 202.048 | high | 1.931 | 3.736 | PASS |  |
| 20190624_151944 | 2 | 151.471 | high | 2.115 | 3.105 | PASS |  |
| 20190624_152500 | 2 | 101.202 | high | 2.466 | 4.689 | PASS |  |
| 20190523_140705 | 4 | 21.841 | medium | 4.703 | 10.851 | PASS |  |
| 20190523_141008 | 4 | 13.172 | low | 5.858 | 14.869 | PASS |  |
| 20190523_141327 | 4 | 5.930 | low | 7.932 | 4.457 | PASS |  |
| 20190624_143040 | 4 | 201.032 | high | 1.286 | 5.675 | PASS |  |
| 20190624_144245 | 4 | 150.209 | high | 1.579 | 5.637 | PASS |  |
| 20190624_145052 | 4 | 99.981 | medium | 2.073 | 7.280 | PASS |  |
| 20190624_145615 | 4 | 51.488 | medium | 2.872 | 5.600 | PASS |  |

## Scope and interpretation

This protocol evaluates a rigid source vessel discharging through a nominal circular aperture. It does not validate a vehicle-fueling loop, cryogenic two-phase release, a site vent stack, pipe backpressure, ignition, dispersion, or emergency separation distance.

Post-outcome model development must preserve this negative result. Any revised thermophysical domain, heat-transfer model, valve/line model or coefficient requires a new version and independent holdout; the present cases cannot become an undisclosed validation set.

The numerical-only pass fraction is descriptive and does not replace the predeclared decision, which includes every eligible model failure.
