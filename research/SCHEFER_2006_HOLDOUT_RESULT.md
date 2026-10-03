# Schefer 2006 transient mass-flow holdout result

The endpoint-frozen evaluation is **negative**. The locked evaluator was pushed
in commit `89c616e` before any numerical coordinate from the experimental curve
was opened. The experiment's approximate overall duration had been visible in
secondary descriptions and was disclosed in the protocol.

The 25 retained Figure 3b coordinates produced:

| Endpoint | Frozen screen | Observed | Decision |
|---|---:|---:|---|
| Mass-flow NRMSE / measured peak | <= 15% | 5.83% | pass |
| Median absolute percentage error above 10% peak | <= 20% | 22.85% | fail |
| Half-peak crossing-time relative error | <= 20% | 28.29% | fail |

Measured and predicted peak flow were 68.38 and 60.67 g/s. The measured
half-peak time was 13.35 s; the model predicted 9.58 s. All three screens were
required, so the transient mass-flow claim is not supported by this holdout.

The error direction is physically informative: the adiabatic model starts below
the measured peak and decays faster. This is consistent with missing heat input
from the two cylinder walls and possible inventory/pressure dynamics in the
published 7.6 m downstream tube. It does not authorize post-hoc adjustment of
the frozen `Cd=1.0`, thresholds or measured support. Any non-adiabatic or
line-pack revision must be treated as development and tested on a different,
pre-frozen external experiment.

The conclusion is limited to one approximately 15.5 MPa transient. It does not
validate the flame, radiation, dispersion, 70--90 MPa storage, refuelling
controller or full station loop.
