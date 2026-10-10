# ESST 2020 dispenser data intake result (2026-10-11)

The article page for the 35/70 MPa dispenser study exposes four public CSV ZIP
supplements. They were downloaded only after the outcome-free protocol was
frozen in `esst_2020_dispenser_full_loop_protocol_2026_10_11.json`.

All four ZIP files are valid, but each expands to a three-row summary table:

- T1: 35 MPa initial state;
- T2: 35 MPa final state;
- T3: 70 MPa initial state;
- T4: 70 MPa final state.

The tables contain reported vehicle volume, pressure, temperature, transferred
mass and elapsed time summaries. They do not contain a time axis, station and
vehicle channels on a common clock, a channel/unit dictionary, or a publisher
crosswalk. Consequently this source is accepted as a bounded real-refueling
benchmark and **not** as an external full-loop validation set. No runtime
parameter or readiness gate was changed.

The machine-readable hashes and decision are in
`esst_2020_dispenser_full_loop_result_2026_10_11.json`. The source article is
[Study on comprehensive evaluation of 35 MPa/70 MPa hydrogen dispenser refueling performance](https://esst.cip.com.cn/article/2020/2095-4239/2095-4239-2020-9-3-702.shtml).
