# Jankuj 2026 pressure-decay transfer result

**Decision: INVALIDATED_PRIOR_OUTCOME_ACCESS**

The repository had already recorded the Figure 7 numerical row count and
workbook hash on 2026-10-04. The later transfer protocol is therefore not a
valid prospective protocol, even though its commit predates this particular
archive download. This result is retained only as a post-access diagnostic.
One effective breach diameter
(1.4696 mm) was fitted to
`Pressure n.1`; `Pressure n.2` was evaluated without refitting.

| Holdout metric | Result | Frozen limit | Pass |
|---|---:|---:|---:|
| Pressure NRMSE / initial excess | 81.562% | <= 10% | False |
| Median absolute percentage error | 2836.963% | <= 15% | False |
| Half-pressure time relative error | not reached | <= 25% | False |

The development curve contains 1 pressure jump
of at least 50 bar after the detected release onset. The protocol required all
finite post-onset samples to remain, so this discontinuity was not trimmed. The
holdout also contains 106 samples
that become non-positive after the frozen gauge-to-absolute conversion. These
observations make the public columns unsuitable for the assumed two-repeat
transfer design and the failed result is retained.

This result does not validate breach geometry, ignition probability, flame
length, consequence distance, H70 release, station operation, emergency action
or SAGA effectiveness.
