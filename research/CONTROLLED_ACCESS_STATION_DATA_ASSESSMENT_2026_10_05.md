# Controlled-access station data assessment

The local source folder `Desktop/DocuData/수소충전소 데이터` was inspected in
place. Raw files were not copied into this repository, parsed values were not
published, and the audit artifacts remain outside the public worktree.

## Inventory and usefulness

| Source | Local coverage | Signals | Model value | Boundary |
|---|---|---|---|---|
| Korean HRS A / pressure logger | 12 monthly CSV segments from May 2024 to April 2025, nominal 1 s rows | two flow accumulator/rate pairs, two auxiliary pressures, medium-bank pressure `PI_2005`, high-bank pressure `PI_3002_XQ` | fit pressure noise, cascade-bank boundary conditions, recharge/dispensing event segmentation and flow-rate plausibility | no vehicle pressure, SOC, nozzle temperature or complete valve/controller state |
| Korean HRS A / life-cycle logger | 12 distinct monthly segments plus one byte-identical duplicate | HP/MP bank cycle counters and five bank temperature channels | add cycle-based degradation and thermal aging state; test pressure–temperature–cycle relationships | cycle definition is full-charge based; no per-event vehicle/fueling labels |
| Korean HRS B / compressor and station logger | 8 daily CSV files, 21–28 April 2025, mostly 1 s rows | 64 channels: compressor pressures/temperatures, HP/MP pressure, chiller temperatures, mass-flow meter fields, valve states, loads, alarms and oil-pressure status | calibrate compressor, precooler, valve-transition and ESD/abnormal-state logic; derive station operating-mode labels | no explicit vehicle tank/SOC or dispenser protocol trace; first timestamp header is encoding-corrupted and must be mapped manually |

The supplied description identifies the tags but does not provide a complete
machine-readable unit dictionary. The apparent pressure ranges are physically
plausible for bar-scaled MP/HP instrumentation, but the implementation must not
silently assume bar or MPa. Unit, scaling, calibration, quality flags and tag
semantics must be confirmed with the custodian before fitting or validating the
model. The same applies to `MFM`, `MFM_F`, timer-like fields and the first
timestamp header in the HRS B files.

The files contain roughly **33 file entries and 5.1 GB** of raw CSV data,
including one exact duplicate life-cycle segment. The local metadata audit
records file hashes, row counts, channel names and time coverage without
retaining raw rows in the repository:

`C:\Users\lyul\Desktop\ProjectData\external_hrs_quarantine\kohygen_hwasung_metadata_2026_10_05.json`

The channel-level assessment is kept at:

`C:\Users\lyul\Desktop\ProjectData\external_hrs_quarantine\kohygen_hwasung_channel_audit_2026_10_05.json`

## Recommended model extensions

1. **Station-side boundary replay.** Add a controlled-access adapter that maps
   Korean HRS B pressure, temperature, chiller, valve and compressor fields to
   the virtual compressor/cascade/header states. Resample short 2–3 s logger
   gaps explicitly; never silently interpolate alarm or valve states.
2. **Cascade dispatch calibration.** Use Korean HRS A `PI_2005` and
   `PI_3002_XQ` with the two flow-rate fields to estimate bank-switch hysteresis,
   pressure-drop dynamics and flow-unit conversion. The current model should
   expose these as measured-boundary or station-controller tests, not overwrite
   vehicle-side validation results.
3. **Precooler and compressor transients.** Use HRS B chiller inlet/outlet
   temperatures, compressor discharge pressures and load flags to identify
   start-up, steady, recharge and trip modes. Fit only global parameters on a
   development split; reserve untouched event windows for validation.
4. **Aging state.** Treat HP/MP life-cycle counters as an optional slow state
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
