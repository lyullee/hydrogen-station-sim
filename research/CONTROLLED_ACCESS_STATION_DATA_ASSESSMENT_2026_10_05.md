# Controlled-access station data assessment

An owner-controlled source folder was inspected in place. Raw files were not
copied into this repository, parsed values were not published, and the audit
artifacts remain outside the public worktree. The public record deliberately
omits the operator, site, country, exact dates, manufacturer, model numbers,
tag names, dimensions and other re-identifying details.

## Inventory and usefulness

| Source | Local coverage | Signals | Model value | Boundary |
|---|---|---|---|---|
| Confidential station dataset A / pressure logger | Multi-month interval, approximately one-second sampling | several storage-pressure and flow-related signals | fit pressure noise, cascade-bank boundary conditions, recharge/dispensing event segmentation and flow-rate plausibility | no vehicle pressure, SOC, nozzle temperature or complete valve/controller state |
| Confidential station dataset A / life-cycle logger | Multi-month interval with a repeated archival segment | storage-bank cycle counters and several temperature channels | add cycle-based degradation and thermal-aging state; test pressure–temperature–cycle relationships | cycle definition is owner-specific and must be confirmed; no per-event vehicle/fueling labels |
| Confidential station dataset B / equipment logger | Multi-day interval, approximately one-second sampling | dozens of channels covering compressor pressures/temperatures, storage pressure, cooling, flow-related signals, valve states, loads and alarms | calibrate compressor, precooler, valve-transition and ESD/abnormal-state logic; derive station operating-mode labels | no explicit vehicle tank/SOC or dispenser protocol trace; one timestamp field requires owner-confirmed decoding |

The supplied metadata include signal names but do not provide a complete
machine-readable unit dictionary. The apparent pressure ranges are physically
plausible for bar-scaled MP/HP instrumentation, but the implementation must not
silently assume bar or MPa. Unit, scaling, calibration, quality flags and tag
semantics must be confirmed with the custodian before fitting or validating the
model. The same applies to flow-meter fields, timer-like fields and one
timestamp field that requires custodian-confirmed decoding.

The files comprise several gigabytes of raw time-series data. The local
metadata audit records file hashes, row counts and broad time coverage without
retaining raw rows in the repository. The public project intentionally does
not reproduce those hashes, filenames or exact counts.

The owner-controlled metadata audit is stored outside the public worktree.

The channel-level assessment is also stored outside the public worktree.

## Recommended model extensions

1. **Station-side boundary replay.** Add a controlled-access adapter that maps
   confidential equipment pressure, temperature, cooling, valve and compressor fields to
   the virtual compressor/cascade/header states. The initial adapter now lives
   in `src/h2station/controlled_station_replay.py`; resample short logger gaps
   explicitly and never silently interpolate alarm or valve states.
2. **Cascade dispatch calibration.** Use the confidential storage-pressure and
   flow-related signals to estimate bank-switch hysteresis,
   pressure-drop dynamics and flow-unit conversion. The current model exposes
   the resulting margin as an explicit `ReferenceScenario` option; it must not
   overwrite vehicle-side validation results or silently change the default.
3. **Precooler and compressor transients.** Use the confidential cooling
   temperatures, compressor discharge pressures and load flags to identify
   start-up, steady, recharge and trip modes. Fit only global parameters on a
   development split; reserve untouched event windows for validation.
4. **Aging state.** Treat owner-defined storage-cycle counters as an optional slow state
   affecting capacity, heat transfer and leak/relief thresholds. The source
   description defines a cycle as a full charge, so it must not be treated as
   an equivalent operating-hour counter.
5. **Event and fault labels.** Derive candidate compressor/chiller/valve
   transitions and oil-pressure trips. Confirm each label with the data owner
   before using it as a failure or safety outcome; zero-valued alarm channels
   are absence of recorded alarm, not proof that no incident occurred.

## What is still missing for full-loop validation

The source data do not expose a synchronized vehicle-side pressure/temperature,
SOC, dispenser nozzle temperature, protocol state or complete mass-flow path.
They can materially improve station-side physics and operational realism, but a
full station-to-vehicle IJHE validation still needs either those channels from
the same events or a separately approved vehicle-side dataset.

## Controlled-use requirements

Use the workflow in
[`CONFIDENTIAL_REAL_DATA_VALIDATION_PROTOCOL_2026_10_05.md`](CONFIDENTIAL_REAL_DATA_VALIDATION_PROTOCOL_2026_10_05.md):
quarantine and hash the files, freeze model/scoring/case selection before
outcome access, preserve failed events, and publish only custodian-approved
derived results. The local files must never be copied into GitHub or Zenodo.
