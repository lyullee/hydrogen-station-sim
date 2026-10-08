# Confidential station lifecycle/pressure alignment protocol

This protocol prospectively tests a joint relationship that had not been
computed when the protocol was frozen: whether owner-attested medium/high
storage pressure completion events align with owner-defined full-bank recharge
counter increments on the shared local logger clock.

Individual pressure-cycle distributions and one limited counter-window summary
were already known. Full-archive event matches, recall, precision and timing
offsets were not. The detector, split, matching window, eligibility thresholds
and pass criteria are locked in
`confidential_station_lifecycle_pressure_alignment_protocol_2026_10_08.json`
before the joint source files are evaluated.

The first 70% of the mapped time range is calibration and the last 30% is the
untouched holdout. A completion is counted after pressure reaches 99% of the
owner-attested full-bank threshold and is rearmed only after a 0.50 MPa drop.
Counter events are positive integer increments. Events are matched one-to-one
to the nearest pressure completion within 300 seconds, separately for each
bank and partition. Exact duplicate source payloads are excluded.

A pass supports only the same-site storage recharge event detector. It does not
validate vehicle filling, compressor capacity, storage geometry, degradation,
failure probability, safety limits, independent-site transfer or field
certification. Failure is retained without outcome-driven threshold fitting.
