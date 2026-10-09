# Local station-data custodian attestation request

This checklist is the next controlled intake step for the owner-controlled
station archive. It requests only generic channel semantics and aggregate
quality information. It does not request raw rows, site identity, equipment
identity, exact dates, absolute timestamps or raw tag names.

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

Until these confirmations are supplied, the current evidence remains valid for
station-side pressure cycles, cascade ordering and recharge-response diagnostics
only. It must not be promoted to vehicle-fill accuracy, full-loop validation,
field safety distance, safety-limit certification or production retuning.

The machine-readable version is
[`local_station_custodian_attestation_request_2026_10_09.json`](local_station_custodian_attestation_request_2026_10_09.json).
