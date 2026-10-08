# Local hydrogen-station data discovery recheck (2026-10-09)

The local scan found a substantial measured station-side bundle, plus adjacent hydrogen-process material and two browser-exported simulator traces. The evidence classes are kept separate so the application does not mistake a simulator export for independent validation data.

## What is available

- **Measured station telemetry:** 33 CSV files, 4.749 GiB, 59,272,300 physical rows and 56,854,143 rows after duplicate exclusion. The 25 narrow and eight wide schemas cover pressure, temperature, flow/mass-like, compressor/load-like, valve/ESD-like, lifecycle and totalizer-like families. Pressure units and lifecycle event semantics are attested; flow units and vehicle-side channels are not.
- **Derived simulator exports:** two local CSV exports with 337 and 339 rows and eight vehicle/dispenser-oriented fields. They match the application export schema and contain zero leak flow in both exports, so they are suitable for UI/export regression only. They are not independent measured data.
- **Adjacent liquid-hydrogen operations:** 52 qualitative scenario steps, 28,121 operation-sequence rows, 18,086 minute-trend rows, 6,740 timestamp/differential rows and 94,389 recovered storage rows. These support virtual HAZOP/action sequencing and trend plausibility after provenance review, but are not a synchronized GH2 dispenser cohort.
- **Engineering and visual context:** 22 engineering documents, 54 images and three videos for de-identified topology, equipment scale and camera placement.

The local data are therefore **not sparse**. The limiting issue is alignment: the measured bundle is station-side, while a full-loop validation cohort still needs synchronized measured vehicle pressure/temperature and delivered mass or SOC. The two Downloads CSV files must stay outside that validation gate because they are derived simulator exports.

## Safe reuse boundary

Use the measured bundle for station-side pressure-cycle, cascade, recharge and state-transition holdouts. Use the adjacent LH2 material for qualitative HAZOP and virtual response training. Use the simulator exports only for export, plotting and vehicle-side UI smoke tests. Do not publish raw rows, source paths, file names, site/company/manufacturer identifiers or exact calendar dates.

See [`local_hydrogen_station_data_discovery_recheck_2026_10_09.json`](local_hydrogen_station_data_discovery_recheck_2026_10_09.json) for the machine-readable, privacy-bounded inventory.
