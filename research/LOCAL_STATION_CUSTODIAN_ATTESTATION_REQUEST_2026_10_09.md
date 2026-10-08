# Local station custodian attestation request (privacy bounded)

The local archive is substantial enough for station-side validation: 33 CSV
files, 32 unique payloads after duplicate exclusion, and 56,854,143 retained
rows. The current screen supports station pressure cycles, cascade ordering,
short-horizon pressure forecasts, conditional recharge-flow episodes, and
equipment-state continuity. It does not yet support a station-to-vehicle
full-loop claim because channel meaning and vehicle-side coverage are not
closed.

This checklist requests only generic semantics and aggregate quality metadata.
It deliberately does not request raw rows, source paths, channel tags, site or
company identity, manufacturer details, calendar dates, or absolute
timestamps. Raw data remain under the custodian's control.

## Required confirmations

1. **Timebase and event alignment** – common clock, offset handling, reset
   behavior, and whether a shared de-identified operation/event identifier
   exists. Acceptance is a timebase contract and event-boundary rule.
2. **Pressure reference and units** – role-level unit, absolute/gauge
   reference, scale, valid range, and calibration/quality flag definition.
3. **Temperature roles and units** – gas/wall/ambient/compressor/cooler role,
   location class, units, and degC/K conversion rule.
4. **Flow and totalizer semantics** – mass or volume, units, sign convention,
   direction, and reset/rollover behavior, plus one aggregate closure statistic.
5. **Equipment state and ESD semantics** – generic meanings for compressor,
   cooler, valve, ESD and trip states, including failed-feedback values.
6. **Vehicle/dispenser coverage** – presence of synchronized vehicle or
   receptacle pressure, temperature, delivered mass or SOC, dispenser flow,
   and fill-event identifiers. A presence/absence matrix is sufficient.
7. **Calibration and quality metadata** – uncertainty, missing-value codes,
   maintenance windows, calibration interval, and sensor replacement rules.
8. **Rights and review scope** – permission for reviewers to inspect derived
   aggregates while raw data remain private and unpublished.

## How the answers change the validation gates

- Pressure and sequence results can remain station-side descriptive until
  units/reference and timebase are confirmed.
- Temperature, flow, state-transition and consequence boundaries stay blocked
  until their corresponding semantics are attested.
- Full station-to-vehicle validation stays blocked until synchronized vehicle
  or dispenser channel families and an event alignment rule are confirmed.
- Safety limits, accident frequencies, production auto-tuning and field
  certification remain outside this checklist.

The machine-readable contract is
`research/local_station_custodian_attestation_request_2026_10_09.json`.
