# Local station-data custodian attestation request

This checklist is the next controlled intake step for the owner-controlled
station archive. It requests only generic channel semantics and aggregate
quality information. It does not request raw rows, site identity, equipment
identity, exact dates, absolute timestamps or raw tag names.

## Current evidence boundary

The local archive is already large enough for station-side validation: 33 CSV
files (25 narrow and eight wide schemas), 59,272,300 physical rows and
56,854,143 rows after duplicate exclusion. The currently supported measured
uses are pressure-cycle behaviour, cascade ordering, recharge-response
diagnostics, compressor/valve/ESD state consistency and chronological station
holdouts. Pressure reference and lifecycle event semantics are attested.

This archive does not yet establish a synchronized vehicle-fill cohort. Flow
units, vehicle-side pressure/temperature/mass/SOC channels, calibration
uncertainty and the complete event clock still require the confirmations below.
The request therefore asks for semantics and aggregate checks, rather than an
export of the confidential rows.

## Required confirmations

1. **Time base and event alignment** — common clock, reset/timezone treatment,
   event boundaries and any shared operation identifier.
2. **Pressure reference and units** — generic storage-bank roles, gauge/absolute
   reference, scale and valid range.
3. **Temperature roles and units** — gas, wall, ambient, compressor discharge
   or cooler outlet, with unit conversion and sensor-location class.
4. **Flow and totalizer semantics** — direction, mass/volume units, reset or
   rollover behavior and one aggregate closure statistic.
5. **Equipment and ESD states** — generic meanings for compressor, cooling,
   valve, ESD and trip states, including failed-feedback values.
6. **Vehicle/dispenser boundary** — presence or absence of synchronized vehicle
   or receptacle pressure, temperature, delivered mass/SOC, dispenser flow and
   fill-event identifiers.
7. **Calibration and quality metadata** — uncertainty, missing-value codes,
   maintenance windows and sensor replacement treatment.
8. **Rights and review scope** — permission to review derived aggregates while
   keeping raw data owner-controlled and unpublished.

## Acceptance format

Return a de-identified role/unit/state matrix and aggregate quality statistics.
Keep the calibration and holdout split frozen before inspecting numerical
outcomes. A hash of the private mapping may be retained outside this repository
for controlled replay.

## What each confirmation enables

| Confirmation | Enabled evidence |
| --- | --- |
| Time base and event rules | Cross-file synchronization, chronological holdouts, incident replay |
| Pressure roles and units | Pressure-envelope and restart-margin evaluation |
| Temperature roles and units | Thermal-boundary and cooler-state holdouts |
| Flow/totalizer semantics | Mass-balance and flow-limited consequence checks |
| Equipment/ESD state dictionary | State-transition and virtual-action replay |
| Vehicle/dispenser channels | Station-to-vehicle pressure/temperature/mass/SOC holdout |
| Quality and calibration metadata | Uncertainty bands and reviewer reproducibility |
| Rights approval | Controlled review and privacy-preserving publication |

## Gate effects

- Confirmations 1–5 allow the measured station profile to be replayed with
  explicit time alignment, state transitions and pressure/thermal/flow roles.
- Confirmation 6 is required before any vehicle, dispenser or full-loop
  accuracy claim is enabled; an absent channel is recorded as a boundary, not
  imputed from the simulator.
- Confirmation 7 is required for uncertainty intervals, missing-data policy
  and reproducible reviewer replay.
- Confirmation 8 permits a de-identified aggregate review while the raw archive
  remains owner-controlled. It does not transfer ownership or authorize
  publication of site, manufacturer or date identifiers.

Until these confirmations are supplied, the current evidence remains valid for
station-side pressure cycles, cascade ordering and recharge-response diagnostics
only. It must not be promoted to vehicle-fill accuracy, full-loop validation,
field safety distance, safety-limit certification or production retuning.

The machine-readable version is
[`local_station_custodian_attestation_request_2026_10_09.json`](local_station_custodian_attestation_request_2026_10_09.json).
