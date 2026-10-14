# New-data search and bounded development decision (2026-10-15)

## Decision

No newly located source supplied a rights-cleared, immediately downloadable raw
cohort that closes the synchronized station-to-vehicle, release-network, or
orientation/HVAC-aware spatial detector validation gaps. Those three validation
lanes are therefore excluded from this development increment and remain stated
paper limitations. Existing runtime coefficients and validation gates were not
changed from plots, aggregate tables, embargoed files, or already-consumed data.

Development proceeded only on functions that need no new empirical outcomes:

1. bounded consequence-input sensitivity with explicit P05/P50/P95 ensemble
   percentiles and ranked input influence;
2. paired automatic response runs using identical initial and fault inputs;
3. a runtime evidence gate that blocks model-driven autonomous actuation when
   site/full-loop validation is absent;
4. partial valve closure, sensor dropout, sensor clock skew, ventilation failure,
   ESD residual-hazard monitoring, and combined-fault regressions.

## Search disposition

| Need | Source checked | Result | Disposition |
|---|---|---|---|
| Spatial hydrogen dispersion/detectors | [GASFLOW-MPI 180-scenario dataset](https://doi.org/10.5281/zenodo.18740541) | Record exists, files embargoed until 2027-05-01 | Excluded until files and rights are available |
| Detector placement/time series | [TU Delft hydrogen sensor-placement thesis](https://repository.tudelft.nl/record/uuid%3A22ee6ff0-af93-42af-ac82-5b8c3d530230) | Thesis PDF, no reusable raw time-series cohort located | Literature context only |
| Ventilation/detector response | HyDelta ventilation publications | Report/table-level evidence; no complete synchronized spatial raw release located | Context only; no validation promotion |
| High-pressure release | [PRESLHY public experimental data](https://preslhy.eu/first-experimental-data-openly-published-by-preslhy/) | Public data already consumed in existing frozen diagnostics | Not an independent new holdout |
| Vehicle/station synchronized boundary | NREL H2FillS publications and public tool pages | Model/publication descriptions located; no new rights-cleared synchronized station-to-vehicle arrays | Retain full-loop limitation |
| Vehicle defuelling boundary | 2026 ZBT publication | Plotted/published results, no reusable raw synchronized cohort located | Literature context only |

## Re-entry conditions

An excluded lane may re-enter only when the raw numeric files are downloadable,
the reuse terms are recorded, required units and time bases are present, the case
has not already been used for fitting or diagnosis, and an outcome-unseen protocol
is frozen before comparison. Until then, software coverage and sensitivity results
must not be described as physical validation.
