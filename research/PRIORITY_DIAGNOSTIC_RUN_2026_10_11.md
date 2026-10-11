# Priority diagnostic run — 2026-10-11

This is a parallel development diagnostic, not a validation-gate update. The
runner completed all five selected diagnostics in 2.865 s. A completed process
is not treated as a scientific pass.

| Diagnostic | Process | Scientific screen | Result |
|---|---|---|---|
| MC SOC/EOS and mass closure | PASS | PASS | 8/8 descriptive cases passed |
| MC measured-boundary tank replay | PASS | **FAIL** | 0/8 joint screens passed |
| Type-III mixed-convection sensitivity | PASS | PASS | 3/3 sensitivity cases passed |
| H2Safe detector spatial response | PASS | **FAIL** | declared joint spatial screen failed |
| NREL H2FillS HDVS tank boundary | PASS | **FAIL** | 0/7 screening cases passed |

The positive MC SOC and Type-III sensitivity results are bounded diagnostics.
They do not replace the frozen external holdouts, select runtime parameters or
establish station-to-vehicle performance. The three negative screens remain
visible as model-boundary evidence: tank boundary transfer and detector spatial
ranking are not yet ready for promotion.

No runtime parameter, alarm threshold or consequence-distance rule was changed
after this run. The machine-readable record is
`research/priority_diagnostic_run_2026_10_11.json`.

## Claim boundary

This run verifies process integrity and records development-level scientific
screens only. It does not establish field safety, evacuation distance, operator
effectiveness, station-to-vehicle full-loop accuracy or journal readiness.
