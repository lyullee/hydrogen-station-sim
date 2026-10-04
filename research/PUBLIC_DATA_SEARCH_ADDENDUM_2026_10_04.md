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
| [CIP 35/70 MPa fueling study](https://esst.cip.com.cn/article/2020/2095-4239/2095-4239-2020-9-3-702.shtml) | Measured 35/70 MPa fueling pressure, temperature and flow curves; linked T3/T4 CSV ZIPs are summary-table exports, not synchronized logger rows | Real experiment aggregate/table-only; raw trace request required |
| [ZBT/MetHyTrucks sampling intercomparison](https://doi.org/10.3390/cleantechnol8030091) | Real test-HRS experiments report logged dispenser/tank channels; raw data are available from authors on request | Strong station-to-receptacle data-request lead; not public raw data |

## Decision

No new eligible public raw full-loop set was found. The CIP article was checked
directly: its T3/T4 “CSV” downloads contain only table rows, while the
pressure/temperature/flow time histories remain figures. The ZBT/MetHyTrucks
article states that raw logged dispenser/tank data are available on request, but
no public machine-readable archive or reuse terms were found. Existing H2Protocol and
NREL files remain governed by their already-frozen roles; they cannot be
reused as a new untouched holdout. The independent full-loop validation gate
therefore remains open. Any future file must be quarantined and hashed with
`scripts/intake_external_hrs_bundle.py` before numerical values are opened.
## 2026-10-04 discovery refresh

The official public inventories found in a second repository search were also
checked against the same intake rule:

| Source | Observed fields | Decision |
| --- | --- | --- |
| [European Hydrogen Observatory HRS workbook](https://observatory.clean-hydrogen.europa.eu/hydrogen-landscape/distribution-and-storage/hydrogen-refuelling-stations) | Station location and dispenser type; no vehicle pressure, gas temperature or mass-flow logger | Static infrastructure context only |
| [California MDHD infrastructure dataset](https://lab.data.ca.gov/dataset/medium-and-heavy-duty-infrastructure) | Station coordinates, dispenser/nozzle counts and funding fields under CC BY | Static infrastructure context only |
| [H2-Stations API v2 documentation](https://docs.h2-stations.eu/for-data-users/) | Static layout plus availability, usage, hydrogen-storage and pricing signals | Operations context only; no synchronized transient fill trace |
| [NREL H2FillS user manual](https://www.nrel.gov/docs/libraries/hydrogen/h2fills-user-manual.pdf?sfvrsn=b2960c3d_1) | Simulator result channels and example output schema | Software documentation, not independent measured station data |

These sources are useful for station topology, equipment mix and operating
context, but none meets the required station-to-vehicle pressure/temperature/
mass-flow time-series rule. They therefore do not change the independent
full-loop gate or justify a publication claim of validated station control.
