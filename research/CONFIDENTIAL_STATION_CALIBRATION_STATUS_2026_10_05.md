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
- `synchronize_station_traces` now requires a real absolute-time overlap before
  combining a pressure logger with an equipment logger. It uses nearest-time
  matching for numeric channels and discrete carry-forward semantics for
  states, while retaining only a de-identified alignment summary for review.
- `scripts/replay_confidential_station_boundary.py` now provides a bounded
  measured-boundary replay. It injects an approved pressure (and, when
  available, temperature) profile into the reference station and writes only
  profile/sample counts, replay duration, and protection status.

## Preliminary result and limits

The pressure-only replay is usable for station-boundary plausibility and for
checking the anti-chatter logic. A second private replay also exercised
equipment-side pressure, temperature and discrete-state channels through the
same adapter. It is not sufficient to refit the complete station model: the
exports do not carry synchronized vehicle-side pressure/temperature/SOC,
dispenser protocol state, or a confirmed unit and calibration dictionary. The
preliminary robust margin stayed at the simulator's existing conservative
floor, so it was **not** applied as a hidden default.

An in-memory pressure-boundary replay was also executed against the reference
scenario using a short relative profile. The simulator produced a normal
trajectory with the measured boundary supplied explicitly; no raw profile,
calendar timestamp, or fitted parameter was persisted, and the production
defaults remain unchanged.

The new bounded replay runner was then exercised with a de-identified private
pressure sample. It completed the requested short horizon and produced three
simulator samples without an ESD trigger. This confirms that the measured
boundary can pass through the complete protection-aware runtime path; it does
not establish independent predictive accuracy or justify changing a frozen
model parameter.

The same runner also accepts the aggregate calibration artifact as an explicit
runtime input. A private replay with that margin enabled completed the same
short horizon, so the measured recharge hysteresis is now testable without
embedding the value in public defaults. It remains an operator-selected
calibration input; it is not silently applied to ordinary simulations.

The first pressure/equipment synchronization attempt was intentionally rejected
because the two supplied sample windows did not overlap on their absolute time
axes. No rows were shifted to manufacture an overlap, and no scenario
parameter was changed as a result. A future same-window export must pass the
overlap and nearest-sample-gap checks before it can be used for boundary
replay.

The next approved calibration pass must combine the equipment logger with the
pressure trace, confirm units and timestamp semantics with the custodian, and
freeze an untouched event window before fitting compressor, precooler, valve,
and ESD parameters. A full-loop claim still requires vehicle/receptacle
channels or a separately approved synchronized source. The private replay
outputs remain outside the repository until the owner approves their derived
aggregates for publication.

## Reproduction boundary

Run `scripts/calibrate_confidential_station_data.py` only in an access-
controlled environment with a private mapping JSON. Supplying the optional
equipment input and mapping also runs the absolute-time overlap gate and emits
only its aggregate alignment result. The output is an aggregate review
artifact. For a controlled partial replay, run
`scripts/replay_confidential_station_boundary.py` with the same private input
and mapping and an output path outside the repository. An owner-approved
aggregate calibration JSON may be supplied with `--calibration`; this changes
only that replay invocation. Do not commit the mapping, raw files, raw hashes,
filenames, or unapproved derived metrics to GitHub or Zenodo.
