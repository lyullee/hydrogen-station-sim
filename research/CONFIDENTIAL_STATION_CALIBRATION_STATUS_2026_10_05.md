# Confidential station calibration status

This note records the first controlled replay of the owner-provided station
time series without naming the operator, site, country, calendar interval,
manufacturer, equipment model, tag names or detailed geometry. Raw rows and
the custodian mapping remain outside the repository.

## What was implemented

- `h2station.controlled_station_replay` reads a custodian-supplied column map
  at runtime and streams a private CSV bundle without copying raw rows.
- Newest-first logger exports are converted to a relative chronological basis;
  numeric channels are aggregated, while valve/ESD states are reserved for
  forward-fill handling and are never linearly interpolated.
- The calibrator reports only aggregate pressure range, sampling gaps, robust
  pressure-noise/ramp statistics and a conservative recharge hysteresis
  recommendation. It explicitly marks that the raw trace is not persisted and
  that source identifiers are not published.
- `ReferenceScenario` accepts an owner-approved dispatch margin and recharge
  hysteresis margin. The default reference behavior is unchanged; measured
  margins are injected only when a controlled replay supplies them explicitly.

## Preliminary result and limits

The pressure-only replay is usable for station-boundary plausibility and for
checking the anti-chatter logic. A second private replay also exercised
equipment-side pressure, temperature and discrete-state channels through the
same adapter. It is not sufficient to refit the complete station model: the
exports do not carry synchronized vehicle-side pressure/temperature/SOC,
dispenser protocol state, or a confirmed unit and calibration dictionary. The
preliminary robust margin stayed at the simulator's existing conservative
floor, so it was **not** applied as a hidden default.

The next approved calibration pass must combine the equipment logger with the
pressure trace, confirm units and timestamp semantics with the custodian, and
freeze an untouched event window before fitting compressor, precooler, valve,
and ESD parameters. A full-loop claim still requires vehicle/receptacle
channels or a separately approved synchronized source. The private replay
outputs remain outside the repository until the owner approves their derived
aggregates for publication.

## Reproduction boundary

Run `scripts/calibrate_confidential_station_data.py` only in an access-
controlled environment with a private mapping JSON. The output is an aggregate
review artifact; do not commit the mapping, raw files, raw hashes, filenames,
or unapproved derived metrics to GitHub or Zenodo.
