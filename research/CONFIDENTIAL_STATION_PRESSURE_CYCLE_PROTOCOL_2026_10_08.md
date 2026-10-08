# Confidential station high-bank pressure-cycle holdout protocol

This protocol was fixed before the narrow-history archive was evaluated for
pressure-cycle outcomes. It tests the existing **4.5 MPa** high-bank recharge
restart margin, which came from a separate eight-file owner-attested equipment
logger analysis. The candidate is not refitted here.

The evaluator samples every 10th native row, detects a completed pressure decline
only after both a 0.25 MPa fall and a 0.25 MPa recovery, and retains cycles with a
0.5--20 MPa drop over 30--21,600 seconds. Each file is split chronologically at
70%; at least 30 calibration cycles, 15 holdout cycles, six matching files and
four holdout files are required.

A pass requires the fixed 4.5 MPa candidate to lie within the holdout P10--P90,
to differ from the holdout median by no more than 20%, and for the calibration
and holdout medians to differ by no more than 25%.

All raw files and the private mapping remain outside the repository. The result
may contain only generic roles, counts, quantiles, metrics and decisions. A pass
is same-site cross-format corroboration. It does not identify compressor state,
validate vehicle filling, establish a safety limit, demonstrate source
independence, or certify field operation. No runtime parameter is changed by
this protocol.
