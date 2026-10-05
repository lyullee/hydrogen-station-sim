# NREL HDVS raw trace boundary (2026-10-05)

The official NREL H2FillS package contains `20220816_hdvs_typeIV_test_result.xlsx`,
a physical 7-tank Type-IV test dated 2022-08-16. The locally screened workbook
has 351 non-empty one-second samples (0–350 s), 42 columns, hose pressure and
temperature, and per-tank inlet pressure/temperature, mass, internal pressure
and internal temperature for tanks 1, 2, 3, 5, 7, 8 and 9. The description
sheet reports 61.5 kg transferred in 279 s from 1.8 to 75.8 MPa at 15 °C.

The file is identified by SHA-256
`1a3fbe64a50c1c97266bfe0372998513ad3ccec5600fab7bc4b9fc68ad4d9d0c` and is
kept under the gitignored raw-data directory. H2FillS is internal-use-only;
the raw workbook is not redistributed and publication of derived metrics needs
written permission from the data owner.

This record makes the useful boundary explicit: a real hose/tank physical
trace can support an independently frozen tank and hose-boundary screen. The
workbook has no station controller or cascade-state trace, ESD/interlock
events, breakaway/nozzle/receptacle channels, vehicle-side protocol commands,
or vehicle telemetry. It therefore remains ineligible for the complete
station-to-vehicle full-loop holdout and for a SAGA effectiveness claim. The
machine-readable record is
[`nrel_hdvs_raw_trace_boundary_2026_10_05.json`](nrel_hdvs_raw_trace_boundary_2026_10_05.json).
