# Local station-data rescan

The owner-controlled local archive was rescanned on 2026-10-09 using the
privacy-bounded inventory scanner. The result reproduces the previously
committed aggregate inventory, so the conclusion that the station data are
substantial is based on a current scan rather than an earlier estimate.

## Current aggregate

- 33 CSV files, 4.749 GiB
- 59,272,300 physical data rows
- 56,854,143 rows after one exact duplicate payload is excluded
- 25 narrow nine-column files and 8 wide 64-column files
- 12 flow/mass candidate files, 20 pressure candidate files, 21 temperature
  candidate files, and 8 compressor plus 8 valve/ESD candidate files
- no vehicle/dispenser header candidate was found by the expanded screen

The expanded header screen is only a structural check. A zero vehicle or
dispenser candidate does not prove that such telemetry is absent; it means the
custodian mapping has not yet identified it in this archive.

## Reconciliation and use

The rescan matches the prior privacy-bounded inventory and utilization counts:
16,770 ordered high-bank pressure cycles, 11,770 paired medium/high episodes,
1,418 short-horizon pressure forecasts, 733 conditional recharge-flow episodes,
and 27 strong instantaneous/totalizer consistency pairs.

This evidence is sufficient for station-side pressure, cascade, recharge,
controller-state and longitudinal replay. It does not close the synchronized
vehicle/receptacle pressure-temperature, delivered-mass/SOC, protocol-state or
full-loop consequence gates. Runtime defaults remain unchanged.

Machine-readable record:
`research/local_station_rescan_2026_10_09.json`.
