# Progress delta — 2026-10-12

- The IJHE reproducibility route was added and executed from commit `0ec83ab`.
- The initial validation-tree full regression completed with 1,449 passed, 0 failed and 20 warnings in 284.33 s; a clean-commit rerun at `afc4fbe` completed with the same 1,449/0/20 result in 279.06 s.
- The public-data refresh required regeneration of the claim/evidence matrix; the matrix generator now writes explicit LF newlines and its audit hash matches the current readiness audit.
- The clean direct LLM route spot check passed 20 tests with 3 warnings; this is software-contract evidence only and does not establish operator effectiveness or field safety.
- Scientific validation status is unchanged: unresolved external-validation gates remain explicit and no threshold, outcome or model parameter was changed to obtain this result.
- The 2026-10-12 Grüne public-source recheck found no complete rights-cleared machine-readable pressure trace; the 51-point digitized early curve still cannot support the required half-pressure endpoint. The gate remains pending and no model or threshold was changed.
