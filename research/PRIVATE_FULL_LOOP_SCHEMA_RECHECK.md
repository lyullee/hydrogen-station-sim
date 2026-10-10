# Private full-loop schema recheck

`private_full_loop_schema_recheck_2026_10_10.json` is an aggregate-only review
of eight authorized private CSV candidates. The recheck deliberately excludes
the repository worktree, reads only enough structure to identify a possible
header, and does not retain rows, original headers, filenames, source paths or
absolute timestamps.

The eight files were readable and collectively contained terms from all
semantic groups, but **zero files contained every required full-loop group in
one header**. Four files had monotonic numeric time columns and no duplicate
time values in the limited integrity check. This is a schema result, not a
model-validation result.

The admission decision remains closed. A future candidate still needs a
custodian attestation for channel roles and engineering units, common-clock
station/dispenser/vehicle event linkage, calibration uncertainty, declared
reuse rights and a frozen outcome-free split before numerical scoring.

The recheck utility is [audit_private_full_loop_schema.py](../scripts/audit_private_full_loop_schema.py).

The separate eight-trace recharge bundle is summarized in
`private_recharge_multitrace_schema_recheck_2026_10_10.json`. It has complete
time, pressure, temperature, flow and controller-state groups with monotonic
time axes, but no vehicle group; it is therefore station-side evidence only.
