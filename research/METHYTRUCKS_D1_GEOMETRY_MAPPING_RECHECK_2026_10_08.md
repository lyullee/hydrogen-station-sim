# MetHyTrucks D1 geometry and mapping recheck

The official 22NRM03 MetHyTrucks Deliverable 1 was reviewed to determine whether
it closes the missing channel/setup crosswalk for the public MetHyTrucks workbook
material already inventoried by this project.

- Source: <https://doi.org/10.5281/zenodo.20540258>
- Review date: 2026-10-08
- Result: `PUBLIC_GUIDANCE_RECHECKED_NO_GEOMETRY_CROSSWALK`

The guide provides useful sampling practice. It recommends documenting the storage
bank, using the nominal delivery temperature and pressure, documenting the fueling
protocol, and identifying abnormal or aborted fills. It does not publish the
synchronized station-to-vehicle channels, engineering units, controller state,
vehicle identifiers, tank geometry, or physical inlet-nozzle diameter required by
the frozen full-loop and thermal-validation protocols.

The source therefore does not change a validation score or IJHE readiness gate.
It supports a narrower implementation decision: the mixed-convection model now
accepts physical geometry explicitly and the coupled dispenser passes the
receptacle state into it. The calibrated constant-UA model remains the default
until an untouched, geometry-resolved dataset is evaluated.

Machine-readable record:
[`methytrucks_d1_geometry_mapping_recheck_2026_10_08.json`](methytrucks_d1_geometry_mapping_recheck_2026_10_08.json)
