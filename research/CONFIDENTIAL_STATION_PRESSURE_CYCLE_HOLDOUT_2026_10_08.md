# Confidential station high-bank pressure-cycle holdout result

The precommitted evaluator at Git commit `1124ed1` read 12 mapped files and
29,361,269 data rows. Only 21 sampled rows were rejected. The method retained
zero qualifying calibration cycles and zero qualifying holdout cycles, so the
frozen 4.5 MPa candidate was **not corroborated** by this first-run method.

The negative decision is retained without lowering the minimum cycle count,
pressure-drop threshold, recovery threshold or acceptance screens. No runtime
parameter changed.

## Post-outcome diagnosis

All 12 matching files contain both positive and negative pressure steps of at
least 0.01 MPa. The unsmoothed state machine nevertheless retained no cycle,
including under a looser diagnostic. Short local reversals interrupted a
decline before a qualifying fall-and-recovery sequence completed. This indicates
a method-resolution problem rather than absence of pressure variation.

That diagnosis was made after the primary result and cannot revise it. A later
method may add a fixed physically motivated temporal filter, but it must be
versioned separately and disclose that the first method failure was already
known.

## Boundary

The public artifact contains no source paths, filenames, headers, tags, dates,
timestamps or raw rows. This same-site station-side diagnostic does not identify
compressor state, validate vehicle filling, establish a safety limit, estimate
accident frequency, certify field operation or support a full-loop claim.
