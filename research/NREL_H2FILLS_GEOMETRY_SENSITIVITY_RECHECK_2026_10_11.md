# NREL H2FillS geometry sensitivity recheck (2026-10-11)

This note records a post-access diagnostic replay of the NREL H2FillS Type-IV
workbook. It is evidence for model triage, not a new confirmatory validation
result. The workbook and the frozen fit are identified by SHA-256 in the
machine-readable companion file
`nrel_h2fills_geometry_sensitivity_recheck_2026_10_11.json`.

## What was compared

Seven tank histories were replayed with three geometry bases:

1. the historical frozen 0.122 m3 per 4.7 kg scaling;
2. a 9.8 kg capacity divided by tabulated hydrogen density at 70 MPa and
   15 °C, retaining the previously frozen effective-volume fit;
3. the same capacity/EOS volume with the effective-volume multiplier fixed to
   one.

The comparison uses the existing screening limits only as diagnostics:
pressure RMSE ≤ 5 MPa, temperature RMSE ≤ 10 °C, and absolute final mass error
≤ 0.5 kg. It does not refit parameters, select a production default, or alter
any validation gate.

## Result

| Geometry basis | Tanks inside diagnostic screen | Aggregate pressure RMSE | Aggregate temperature RMSE | Final mass error | Final pressure error |
|---|---:|---:|---:|---:|---:|
| Historical frozen scaling | 0/7 | 6.164 MPa | 4.625 °C | 0.120 kg | −8.679 MPa |
| Capacity/EOS + frozen effective fit | 7/7 | 3.538 MPa | 4.254 °C | 0.101 kg | −4.649 MPa |
| Capacity/EOS, no volume fit | 7/7 | 0.496 MPa | 4.185 °C | 0.080 kg | +0.569 MPa |

The capacity/EOS variants materially reduce the pressure mismatch in this
post-access replay. That improvement is not independent confirmation because
the workbook was available before this comparison and the geometry rule was
chosen from the same evidence. A new frozen, outcome-unseen protocol is still
required before a capacity-based rule can support a validation claim or replace
the runtime default.

## Scope decision

The historical runtime default and the frozen validation result are unchanged.
The result is retained to prioritize a prospective geometry protocol and to
prevent the legacy frozen volume from being mistaken for a measured vehicle
geometry. It does not close the station-to-vehicle full-loop gate.

