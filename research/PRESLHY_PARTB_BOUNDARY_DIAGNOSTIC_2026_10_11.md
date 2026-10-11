# PRESLHY Part-B boundary diagnostic — 2026-10-11

This is a **post-outcome development diagnostic** for the frozen Part-B
holdout. It does not alter the primary result or the runtime model.

The locked model uses a well-mixed adiabatic vessel, the reported 225 L
volume, HEOS hydrogen properties and a fixed discharge coefficient of 0.8.
The two 2 mm cases fail the frozen half-pressure-time screen because the
model is about 27% faster than the measured trace. The three 4 mm cases pass
that screen with errors of about 15–16%.

The workbooks also contain `P-Innen` and `P-Duese`. After the declared release
start, the median vessel-to-nozzle pressure difference is approximately
0.05–0.06 bar for the 2 mm cases and 0.22–0.29 bar for the 4 mm cases. If the
only changed quantity were the discharge coefficient, the half-time mismatch
would correspond to a sensitivity indicator of roughly 0.583 for 2 mm and
0.673–0.681 for 4 mm, relative to the locked 0.8 value. These are **not fitted
parameters**; they only show that a single free-aperture coefficient does not
explain the diameter-dependent boundary behavior.

The most plausible unresolved boundaries are the valve/nozzle contraction,
instrument location and the distinction between the measured nozzle channel
and the ideal free aperture. The measured nozzle channel is retained as
diagnostic evidence and is not substituted into the primary evaluation after
outcome access.

The frozen scientific decision remains **negative: 3/5 joint primary screens
pass**. This artifact has no effect on the validation gate, runtime
parameters, consequence distance, ignition, dispersion, station control or
vehicle-loop claims.

Machine-readable details and source hashes are in
`preslhy_partb_boundary_diagnostic_2026_10_11.json`.
