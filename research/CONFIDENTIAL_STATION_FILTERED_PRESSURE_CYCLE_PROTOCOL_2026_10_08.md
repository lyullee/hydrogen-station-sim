# Filtered station pressure-cycle protocol, revision 2

The first frozen, unsmoothed detector returned zero retained cycles because
short local pressure reversals repeatedly ended a candidate decline. That result
is preserved. This separately versioned method revision adds a **seven-sample,
70-second causal rolling median** before applying every original cycle and
acceptance threshold unchanged.

The filter is fixed before filtered cycle outcomes are computed. It suppresses
sub-minute instrumentation and controller reversals while retaining the
minute-scale storage depletion/recharge behavior relevant to the existing 4.5
MPa high-bank restart margin. It uses no future samples and the candidate remains
4.5 MPa.

The same 70/30 within-file split, minimum 30 calibration cycles, minimum 15
holdout cycles, minimum six files/four holdout files, P10--P90 containment,
20% candidate-median error and 25% temporal-median-shift screens apply.

Because the first method failure was known, a pass is sequential same-site
method-revision evidence. It is not source-independent external validation,
vehicle-fill validation, a safety limit or field certification. It cannot change
a runtime parameter by itself.
