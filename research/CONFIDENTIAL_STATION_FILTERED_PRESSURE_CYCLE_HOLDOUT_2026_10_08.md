# Filtered station pressure-cycle holdout, revision 2 result

The hash-locked seven-sample causal-median revision read all 12 matching files
and 29,361,269 data rows, but again retained zero cycles. The result is preserved
as a failed method run and no threshold, candidate or runtime parameter changed.

## Post-outcome order diagnosis

All 12 files are stored in strictly reverse chronological order. Their sampled
absolute time step is 10 seconds, as expected, but the detector required
increasing time and therefore reset at every sample. No chronologically ordered,
filtered cycle result had been computed when this defect was identified.

The correction is unambiguous: sort each file by timestamp before the already
fixed causal filter and cycle detector. A third protocol must lock that ordering
step and retain the same 4.5 MPa candidate, filter, eligibility criteria and
primary screens. Revision 2 is not rewritten or promoted after the diagnosis.

## Boundary

This artifact contains no source path, filename, header, tag, date, timestamp or
raw row. The ordering diagnosis does not itself corroborate the recharge margin,
validate a vehicle fill, establish a safety limit or certify field operation.
