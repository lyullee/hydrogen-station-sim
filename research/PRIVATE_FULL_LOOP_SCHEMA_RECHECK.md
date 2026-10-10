# Private full-loop schema recheck

`private_full_loop_schema_recheck_2026_10_10.json` is an aggregate-only review
of the authorized private CSV candidates currently present. The recheck deliberately excludes
the repository worktree, reads only enough structure to identify a possible
header, and does not retain rows, original headers, filenames, source paths or
absolute timestamps.

The broad inventory scan found time, pressure, temperature, flow and controller
terms, but **zero files contained every required full-loop group in one header**.
The stricter role-aware contract also found **zero files** with explicit vehicle
pressure/temperature, station/dispenser pressure, delivered-gas temperature,
vehicle identity and storage/controller channels co-located. This prevents a
generic `pressure` plus `vehicle` label from being mistaken for a synchronized
station-to-vehicle trace. The limited monotonic-time check is an integrity hint,
not a model-validation result.

The admission decision remains closed. A future candidate still needs a
custodian attestation for channel roles and engineering units, common-clock
station/dispenser/vehicle event linkage, calibration uncertainty, declared
reuse rights and a frozen outcome-free split before numerical scoring.

The recheck utility is [audit_private_full_loop_schema.py](../scripts/audit_private_full_loop_schema.py).

The separate eight-trace recharge bundle is summarized in
`private_recharge_multitrace_schema_recheck_2026_10_10.json`. It has complete
time, pressure, temperature, flow and controller-state groups with monotonic
time axes, but no role-aware vehicle/station contract; it is therefore
station-side evidence only.
