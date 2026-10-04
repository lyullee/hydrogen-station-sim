# MC Default measured-boundary diagnostic (2026-10-05)

This record compares four replay configurations for the eight Powertech Labs
SAE J2601 MC Default traces already consumed by the frozen full-loop study.
Measured source-pressure and inlet-temperature traces are supplied as boundary
inputs; one run also supplies the published protocol pressure schedule. The
maximum gas-temperature sensitivity is changed only as a diagnostic.

All runs are **post-outcome development diagnostics**. They do not change the
frozen holdout, use case-specific fitting, or qualify as independent full-loop
validation.

| Run | Source boundary | Protocol schedule | Gas stop | P RMSE (MPa) | T RMSE (°C) | SOC RMSE (pp) | Pass (8) |
|---|---|---:|---:|---:|---:|---:|---:|
| source 1 | `source_pressure_1_mpa` | no | 95 °C | 6.045 | 14.324 | 7.961 | 0 |
| source 3 | `source_pressure_3_mpa` | no | 95 °C | 5.560 | 14.525 | 7.488 | 1 |
| source 3 sensitivity | `source_pressure_3_mpa` | no | 200 °C | 5.857 | 15.075 | 7.880 | 1 |
| source 3 + schedule | `source_pressure_3_mpa` | yes | 95 °C | 4.908 | 14.756 | 5.914 | 1 |

The measured source boundary reduces some pressure error, but it does not
resolve the joint temperature/SOC mismatch. The protocol-schedule run has the
lowest pressure RMSE but still fails the temperature and SOC screens. Raising
the temperature stop limit increases coverage without producing agreement, so
the safety limit cannot be used as a tuning lever. The result supports a
structural diagnosis: source topology, valve dispatch/controller behavior,
thermal boundary and vehicle-tank representation remain non-identifiable from
the public channels.

The source-pressure result paths are ignored raw-output directories and are
recreated with `scripts/run_partial_station_validation.py`; the committed JSON
records the exact options and aggregate values. A new independent synchronized
station-to-vehicle archive, written reuse rights, frozen no-fitting scoring and
expert/SAGA effectiveness review are still required before the IJHE objective
can be marked complete.
