# Local hydrogen-station data catalog (2026-10-09)

The local collection is **not small**. The limiting issue is synchronization and
semantic attestation at the station-to-vehicle boundary, not the number of rows.
This catalog is an index of the privacy-bounded inventories; it does not expose
paths, filenames, tags, dates, site identity, manufacturer information or raw
measurements.

## What is available

| Evidence class | Aggregate size | Defensible use | Current boundary |
| --- | ---: | --- | --- |
| Owner-controlled station telemetry | 33 CSV files; 4.749 GiB; 59,272,300 physical rows; 56,854,143 after exact-duplicate exclusion | Storage pressure cycles, cascade/recharge chronology, temperature/flow-like trends, compressor/load, valve/ESD and lifecycle state screening | Station side is substantial; vehicle/dispenser channels are not attested |
| Local operational/scenario workbooks | 3 scenario tables with 52 steps; 21 operation sheets with 28,121 non-empty rows; 39 minute-trend sheets with 18,086 rows; 10 timestamp/differential sheets with 6,740 rows; 8 recovered-storage sheets with 94,389 rows | Virtual HAZOP action mapping, response-sequence replay, trigger persistence and trend-shape checks | Some values are reconstructed or have unresolved unit/provenance fields; not a synchronized H70 fueling cohort |
| Engineering/context material | 22 documents, 54 images, 3 videos | De-identified topology, equipment scale, 3D/CCTV/gas-detector placement and HAZOP node naming | Context only; no dynamic validation |
| Operational video collection | 26 files; 17 complete/readable, 9 incomplete/unreadable | Qualitative CCTV/operator-sequence review and visual timing cross-check | Not telemetry; incomplete files stay outside quantitative validation |
| Adjacent hydrogen/utility telemetry | About 2.41 million rows, 273 signal keys over a 24-hour window plus one engineering workbook | Upstream/utility plausibility and equipment-state context | Does not provide a synchronized dispenser/vehicle event |
| Locally cached public validation material | 255 machine-readable files, about 3.509 GB | Component tank/refueling, release/fire/dispersion/detector and operational checks | Heterogeneous component evidence, not one full-loop station trace |
| Browser-exported simulator traces | 2 small CSV exports (337 and 339 rows) | Export, plotting and UI smoke tests | Derived data; never external validation or calibration evidence |

## What has already been corroborated

- The station telemetry rescan reproduces the committed aggregate inventory and
  has no detected inventory drift.
- The station-side pressure-cycle transfer screen contains 16,770 ordered
  high-bank cycles in the calibration bundle and 225 cycles in a separate
  station-side transfer bundle. The result supports station-side transfer
  screening only; it is not independent external validation.
- A broad local discovery screen covered 38,528 machine-readable files and
  12,804 CSV/TSV headers. After a refined screen, zero candidates met all four
  full-loop requirements: common time base, pressure, temperature and flow/mass
  at an attested station/dispenser/vehicle boundary.

## What is still missing for full-loop validation

One independently attested synchronized event containing, on the same time base:

1. station or dispenser pressure;
2. receiving vehicle/receptacle pressure and temperature;
3. delivered mass or an attested mass-flow channel;
4. initial conditions and controller/protocol state; and
5. custodian confirmation of units, roles, reuse rights and calibration status.

Until those fields are supplied, the runtime keeps station-side calibration and
vehicle-side/full-loop claims separate. No raw local rows are imported into the
public repository and no safety limit or consequence distance is inferred from
the inventory alone.

## Linked machine-readable inventories

- [`local_station_asset_screen_2026_10_09.json`](local_station_asset_screen_2026_10_09.json)
- [`local_station_rescan_2026_10_09.json`](local_station_rescan_2026_10_09.json)
- [`local_hrs_corpus_inventory_2026_10_09.json`](local_hrs_corpus_inventory_2026_10_09.json)
- [`local_data_deep_scan_2026_10_09.json`](local_data_deep_scan_2026_10_09.json)
- [`local_docudata_full_discovery_2026_10_09.json`](local_docudata_full_discovery_2026_10_09.json)
- [`local_station_cross_bundle_transfer_result_2026_10_09.json`](local_station_cross_bundle_transfer_result_2026_10_09.json)

