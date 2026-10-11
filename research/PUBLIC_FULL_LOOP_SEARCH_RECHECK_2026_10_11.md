# Public full-loop search recheck — 2026-10-11

## New high-value lead

The Cal State LA study [Genovese et al. (2021)](https://doi.org/10.1016/j.jclepro.2021.129737) describes a real station-to-vehicle acquisition path. Its full text lists per-fueling vehicle pressure, vehicle-tank temperature, final pressure, fill rate, dispensed mass, storage pressures, 35/70 MPa hose pressure/temperature, flow, density, APRR, and tank/hose/blowdown/booster/chiller command or valve states.

The article and the [OSTI record](https://www.osti.gov/biblio/1977265) do not expose a rights-cleared machine-readable logger archive. The source is therefore recorded as a **custodian request lead**, not as an external holdout. No model parameter, runtime behavior, or validation gate was changed.

## Decision

The synchronized station-to-vehicle raw-data requirement remains outside the primary goal until a custodian supplies at least three de-identified events with a common clock, channel dictionary, units, initial conditions, controller/ESD states, checksums, and written reuse permission. After receipt, the protocol and scoring thresholds must be frozen before numerical rows are opened.

Machine-readable records: `public_full_loop_search_recheck_2026_10_11.json` and `external_full_loop_data_recheck_2026_10_11.json`.
