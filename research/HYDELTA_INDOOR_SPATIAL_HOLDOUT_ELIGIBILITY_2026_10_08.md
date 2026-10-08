# HyDelta D6A.1 indoor spatial holdout eligibility

Decision: **INELIGIBLE_NO_MODEL_EVALUATION**.

The report is a strong public actual-hydrogen source, but it cannot be scored as the frozen independent spatial holdout. It reports 50 sensors across 32 hydrogen configuration/flow combinations; however, the exact source and sensor coordinates, release orientation and per-sensor numeric responses required before access are not published as tables or companion data.

| Frozen requirement | Result |
|---|---|
| `minimum_hydrogen_experiments` | PASS — 32 |
| `minimum_mapped_sensors_per_experiment` | PASS — 50 |
| `source_coordinates` | FAIL — top-view blue-dot figure only |
| `sensor_coordinates_in_same_frame` | FAIL — layout photographs/figures and height groups; no tabulated numeric per-sensor coordinates or report companion data |
| `release_orientation_class` | FAIL — gas-valve photograph/schematic without a declared orientation class |
| `per_sensor_numeric_response` | FAIL — multi-sensor plots plus colour-coded final-concentration categories; no tabulated per-sensor maximum, plateau or release-window mean |

No graph or colour-table digitisation was used. The locked formula was not changed, the model evaluation was not run, and the candidate remains disabled at runtime.

## Evidence retained

The report remains useful as actual-hydrogen evidence for concentration stratification, multi-height detector coverage, compartment connectivity and ventilation effects. These are report-level physical-context claims only.

## Next data requirement

Obtain a rights-cleared companion export containing experiment ID, sensor ID, source XYZ, sensor XYZ, release orientation and per-sensor numerical H2 response, or freeze the same candidate against another untouched actual-hydrogen cohort.

Source: [HyDelta D6A.1, DOI 10.5281/zenodo.8154318](https://doi.org/10.5281/zenodo.8154318).

## Claim boundary

HyDelta D6A.1 is retained as public actual-hydrogen report-level evidence for indoor concentration stratification, sensor coverage and ventilation context. It does not independently validate the frozen spatial ranker because the report does not publish the machine-readable spatial outcome fields required by the pre-access protocol.
