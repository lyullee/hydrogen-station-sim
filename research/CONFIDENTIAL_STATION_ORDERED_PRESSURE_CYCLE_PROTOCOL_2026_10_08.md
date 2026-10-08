# Chronology-corrected station pressure-cycle protocol, revision 3

The first unsmoothed and filtered runs both retained zero cycles. A subsequent
order-only diagnostic found that all 12 matching source files are stored newest
to oldest. The detectors required increasing time and therefore reset at each
sample. Chronologically ordered cycle outcomes were not computed before this
revision was frozen.

Revision 3 performs a stable ascending timestamp sort within each file and
retains the last source-order observation at duplicate timestamps. It then uses
the already frozen seven-sample causal median, 4.5 MPa candidate, cycle
definition, 70/30 split, eligibility criteria and primary screens without any
change.

A pass is sequential same-site, cross-format corroboration after a deterministic
source-order correction. The first two failures remain in the record. This is
not source-independent external validation, vehicle-fill validation, a safety
limit or field certification, and it cannot change a runtime parameter by
itself.
