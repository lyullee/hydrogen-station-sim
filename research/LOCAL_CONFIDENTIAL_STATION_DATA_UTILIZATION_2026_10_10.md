# Local confidential station-data recheck (2026-10-10)

This recheck reads the owner-controlled archive outside the repository and
writes only aggregate, privacy-bounded evidence. Source paths, filenames,
original tags, calendar values and measurement rows are not retained.

## Evidence found

- 33 CSV exports, 59,272,300 data rows and 4.749 GiB of source data.
- 32 unique payloads; one exact duplicate export was excluded from the
  deduplicated count.
- 20 files contain pressure candidates, 21 temperature candidates, 12
  flow/totalizer candidates, and 8 controller/valve candidates.
- 25 files have a parseable monotonic time axis. The remaining files are
  lifecycle/temperature segments whose time semantics still require mapping.
- The archive supports station-side pressure, cascade, flow, temperature and
  controller-state analysis. No vehicle/receptacle channel was identified by
  the header-only screen.

## Decision

The local archive is **not sparse** and is suitable for station-side dynamic
validation. It is not yet a station-to-vehicle full-loop holdout: vehicle
pressure/temperature/mass or SOC, common-clock linkage, units, calibration and
rights for a frozen independent split are still unconfirmed. The runtime must
therefore keep vehicle/full-loop claims disabled and must not fit production
parameters from this inventory alone.

The machine-readable source record is
`research/local_confidential_station_data_utilization_2026_10_10.json`.
