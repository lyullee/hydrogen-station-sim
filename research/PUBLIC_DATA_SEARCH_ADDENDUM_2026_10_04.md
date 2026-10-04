# Public HRS data search addendum — 2026-10-04

This addendum records a targeted search for a new, independent station-to-
vehicle raw logger archive. The full-loop gate requires a common time base for
vehicle or receptacle pressure, temperature, and mass flow/transferred mass,
plus initial conditions, protocol metadata, units and reuse terms. A paper,
plot, availability feed, aggregate log, or component-only release does not meet
that rule.

## Sources checked

| Source | What is public | Classification |
| --- | --- | --- |
| [Oh et al. KGS HRS study](https://doi.org/10.1007/s11814-025-00551-9) | Six Korean operating-HRS scenarios and pressure/temperature/flow comparisons are reported; the synchronized KGS logger export is not included | High-value data-request lead |
| [HySam measurement data, Zenodo 10.5281/zenodo.20590842](https://zenodo.org/records/20590842) | Three XLSX sampling-system experiments with pressure/temperature conditions | Sampling-system data, not vehicle fueling |
| [Hydrogen dispersion experiment, DOI 10.23642/USN.26117989](https://doi.org/10.23642/USN.26117989) | Release mass flow, filling pressure and 29 hydrogen-concentration channels | Consequence-model candidate, not HRS full loop |
| [H2-Stations API](https://docs.h2-stations.eu/for-data-users/) | Licensed station inventory, availability and selected storage/usage status | Station status data, not synchronized transient logger data |
| [NREL H2IQ high-flow experiment](https://www.energy.gov/sites/default/files/2024-04/h2iqhour-03262024.pdf) | Real high-flow operating-range plots and summary values | Plot/aggregate benchmark; raw trace request required |
| [PRHYDE/ZBT D6.7](https://lbst.de/wp-content/uploads/2023/04/PRHYDE_Deliverable-D6-7_Results_as_Input_for_Standardisation_V1-2_final_Apr_2023.pdf) | Public report tables for 35/50/70 MPa ZBT tests and a stated 2 Hz PLC logger | Public report/data-request lead; raw synchronized export and reuse terms still required |
| [KIT H2 release archive, DOI 10.35097/1483](https://doi.org/10.35097/1483) | Public 5 GB experiment metadata lists pressure, mass flow, heat flux, thermocouples, weather and video; CC BY-SA 4.0 | Consequence/detector submodel candidate; not vehicle-fueling full loop |

## Decision

No new eligible public raw full-loop set was found. Existing H2Protocol and
NREL files remain governed by their already-frozen roles; they cannot be
reused as a new untouched holdout. The independent full-loop validation gate
therefore remains open. Any future file must be quarantined and hashed with
`scripts/intake_external_hrs_bundle.py` before numerical values are opened.
