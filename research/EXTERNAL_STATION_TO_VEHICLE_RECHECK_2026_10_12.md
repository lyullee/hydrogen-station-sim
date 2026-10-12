# External station-to-vehicle raw-data recheck (2026-10-12)

The latest public-source recheck did not identify a new eligible synchronized
station-to-vehicle raw archive. Eligibility requires measured station/controller
and dispenser/nozzle channels plus vehicle/receptacle pressure or temperature and
transferred mass/flow on one common clock, with units, initial conditions, tank
capacity, protocol metadata and reuse terms.

- [H2-Stations data-user documentation](https://docs.h2-stations.eu/for-data-users/)
  and the [European Hydrogen Observatory HRS datastream](https://observatory.clean-hydrogen.europa.eu/hydrogen-landscape/distribution-and-storage/hydrogen-refuelling-stations)
  provide public station registry, layout and availability/status context. They
  do not publish synchronized process logger rows.
- The [Cal State LA back-to-back study](https://doi.org/10.1016/j.jclepro.2021.129737),
  the [multi-year HRFF study](https://doi.org/10.1016/j.ijhydene.2023.04.084),
  and the related [OSTI record](https://www.osti.gov/servlets/purl/1799187)
  describe real station logs and vehicle/fueling variables, but the public
  records do not expose a reuse-cleared event-level synchronized export.
- The [NREL H2IQ 2024 heavy-duty result](https://www.energy.gov/sites/default/files/2024-04/h2iqhour-03262024.pdf)
  supplies a valuable plotted single-event protocol and operating-range context,
  but no row-level archive or channel package.
- [DOE/OSTI station data-program records](https://www.osti.gov/servlets/purl/1436732)
  corroborate the station data-acquisition provenance and remain data-request
  leads; they do not constitute a raw holdout.

The count of eligible public synchronized station-to-vehicle raw sets remains
**zero**. This preserves the previously declared scope limitation: the primary
paper may claim station-side and component validation, but must not claim
independent vehicle-controller or complete station-to-vehicle field validation.
The machine-readable evidence is
`research/external_station_to_vehicle_recheck_2026_10_12.json`.
