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

## Decision

No new eligible public raw full-loop set was found. Existing H2Protocol and
NREL files remain governed by their already-frozen roles; they cannot be
reused as a new untouched holdout. The independent full-loop validation gate
therefore remains open. Any future file must be quarantined and hashed with
`scripts/intake_external_hrs_bundle.py` before numerical values are opened.
