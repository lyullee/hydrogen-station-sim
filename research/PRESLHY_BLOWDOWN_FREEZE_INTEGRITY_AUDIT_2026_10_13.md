# PRESLHY E3.1 freeze-integrity audit

The original prospectively frozen evaluation remains the controlling result:

- **11/22 joint passes (50.0%)**, bootstrap 95% CI **31.8%–72.7%**
- predeclared threshold: **70%**
- retained thermophysical-domain failures: **6**
- primary decision: **FAIL**

After the outcomes had been opened, commits `20975ae` and `c7d16d4` changed the
property-domain and restriction choking calculations. Commit `b00c98e` then
reran the consumed cases and obtained 16/22 (72.7%). That later result is useful
development evidence, but it is not a run of the prospectively frozen model and
cannot replace the original decision.

The current runner now checks every frozen model-file hash before opening raw
workbooks, including the pre-outcome validation adapter recorded at commit
`3b01661`. A mismatch fails closed. `--development-diagnostic` permits an
explicitly labelled post-outcome run and prevents archival as external
validation.

This audit does not alter runtime parameters. A revised release model requires a
new, untouched and pre-registered external campaign before a validation claim.
