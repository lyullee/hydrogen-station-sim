# Public operational benchmark face-validity screen

This record compares the locked reference scenario with public HRS endpoint and aggregate observations. It is deliberately narrower than external validation: no parameter is fitted, no plotted trace is digitized, and no aggregate KPI is promoted to a synchronized station-to-vehicle holdout.

The locked reference scenario uses a 70 MPa vehicle target, 45/65/95 MPa cascade-bank targets, a 35 g/s compressor ceiling, and a 60 g/s dispenser ceiling. Public endpoint observations include the CIP 35 MPa and 70 MPa field cases (35.4 and 81.6 MPa final pressure, 36 g/s reported peak), while the DOE/NREL heavy-duty case reports 74.6 MPa and 483.33 g/s peak. The first two support a bounded light-duty operating-range context check; the latter is explicitly outside the default heavy-duty flow envelope.

The checks therefore document nominal compatibility and scope boundaries only. They do not validate pressure or temperature trajectories, protocol timing, consequence distances, or SAGA effectiveness. The source manifest remains the controlling evidence boundary and is hash-linked in the JSON companion.

## Reproducible interpretation

- `PASS`: a public endpoint or peak is numerically compatible with the locked nominal range.
- `CONTEXT`: the comparison is informative but not a pass/fail physics result.
- `NOT_COVERED`: the reference configuration intentionally does not cover the public operating class.
- No item in this screen is a full-loop holdout, calibration result, or safety claim.

The full IJHE readiness audit remains unchanged by design: the raw synchronized external station-loop gate, the component-model failures, institutional/ethics determination, HIAD holdout, expert review, SAGA effectiveness analysis, and submission declarations remain open.
