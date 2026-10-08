# Confidential station cascade-sequence holdout result

The pre-frozen evaluator read all 12 matching reverse-chronological histories,
sorted them into increasing time and retained 8,106 calibration plus 3,664
holdout medium/high pressure pairs.

In the holdout, 70.3939% of the 5,205 high-bank drawdowns paired with a nearby
medium-bank drawdown. Of the paired episodes, 94.3777% followed the declared
medium-to-high order. The median handoff gap was 80 seconds and remained inside
the calibration P10--P90 interval of -70 to 460 seconds. Pair coverage shifted
by 0.003031 and sequential fraction shifted by 0.002806 between calibration
and holdout. Every frozen eligibility and primary screen passed.

This supports the simulator's medium-to-high cascade controller structure as a
same-site pressure-sequence observation. It does not uniquely identify vehicle
fills because the archive has no synchronized vehicle, dispenser or valve-state
channels. The low bank is not owner-attested for this evaluation. No runtime
parameter, safety limit or full-loop validation status changes.

The public result includes no source identity, path, filename, header, tag,
calendar date, absolute timestamp or raw row.
