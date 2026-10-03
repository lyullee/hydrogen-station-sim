# PRESLHY current-revision diagnostic

This artifact records a transparent post-outcome diagnostic of the current
hydrogen-property table boundary handling. It does **not** replace or revise
the prospectively frozen E3.1 validation result in
`research/preslhy_blowdown_external_validation.json`.

## Observation

The frozen E3.1 run evaluated 22 cases, retained six integration failures at
high initial pressure, and produced a 50.0% joint primary pass fraction. The
current implementation was rerun after those numerical outcomes were already
known. It evaluated all 22 cases without integration errors and produced a
72.7% descriptive joint primary pass fraction (bootstrap 95% interval
54.5%–90.9%).

The improvement comes from the bounded table-domain fallback in the real-gas
restriction solver. It is a numerical robustness observation, not evidence
that the revised implementation generalises to unseen experiments.

## Reproducibility

- Protocol SHA-256: `d40cc59af3a607e66870d2afb91014058c83ae96fc1ba4aeac0d8554953733af`
- Current runner commit: `a3a21f0aae77a4d89f78f742f70dd6b905ddcbdc`
- Command: `.venv\Scripts\python.exe scripts/run_preslhy_blowdown_validation.py --output tmp/preslhy_current_diagnostic`
- Raw diagnostic SHA-256: `779df2575ad1da08f4efdd78e40457500668c2595046921833ccbd5c211ed639`

## Claim limit

Because the revised code was executed after the E3.1 outcomes were inspected,
the E3.1 data cannot be reused as a new validation set. The original negative
result remains authoritative. A separate experimental campaign must be frozen
before numerical outcomes are accessed and evaluated with this revision before
the 70% decision threshold can support a revised blowdown claim.
