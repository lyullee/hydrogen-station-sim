# Adjacent local hydrogen operational data recheck (2026-10-09)

The local search found an additional operational telemetry file outside the
measured refueling-station bundle. It is useful as an upstream or site-utility
boundary, but it is not a hydrogen-station-to-vehicle refueling trace.

## Newly identified material

- One machine-readable CSV with about 252.6 MB and 2,410,985 rows.
- One continuous 24-hour UTC-like epoch window, with 273 distinct signal keys.
- The signals include hydrogen-mass and fuel-cell temperature terms, heating and
  hot-water demand, water flow/volume, differential-pressure channels,
  equipment status and thermal-power channels.
- A separate engineering workbook contains static pipeline/metering and
  equipment schedule sheets. It is design/context material, not a synchronized
  time-series logger.

## Valid use in this project

This material can improve the model's upstream boundary description and support
qualitative plausibility checks for hydrogen supply, utility load, differential
pressure and equipment-state transitions. It can also be used to define a
separate upstream-demand scenario or to test resampling and missing-value
handling.

## Boundary that remains closed

The telemetry has no independently attested common event containing a dispenser
controller state, hose pressure, vehicle/receptacle pressure and temperature,
transferred mass or SOC. It therefore cannot close the station-to-vehicle
external-validation gate, and it must not be presented as H70 refueling data.

Raw rows, source paths, filenames, calendar dates and site/manufacturer
identifiers are intentionally excluded from this repository. The machine
readable record contains aggregate counts only.
