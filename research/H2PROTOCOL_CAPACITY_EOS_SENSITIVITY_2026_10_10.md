# SAE J2601 capacity-EOS sensitivity (2026-10-10)

This post-access replay covers 36 public Powertech Labs SAE J2601 Tables Method traces with capacity-EOS vessel geometry and no station/thermal calibration. It is a diagnostic, not certification or field-safety validation.

- Engineering-screening pass: **0/36**.
- Mean pressure RMSE: **25.339 MPa**.
- Mean temperature RMSE: **17.589 °C**.
- Mean SOC RMSE: **32.049 percentage points**.
- Stop reasons: `{'gas-temperature-limit': 34, 'none': 2}`.

Capacity-based geometry is therefore only one repair candidate. The next P1 work must address the declared pressure-ramp/controller boundary, dispenser-flow and precooler calibration, and thermal stop semantics on a prospective split.
