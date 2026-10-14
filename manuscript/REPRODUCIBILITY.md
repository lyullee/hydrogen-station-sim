# IJHE reproducibility route

This repository treats the paper as an evidence-readiness exercise. The
reproduction command checks the committed working manuscript, the compiled PDF
record, the mirrored readiness audit, and (when requested) the software tests.
It does not turn unresolved external-validation gates into a positive result.

## Environment

Use Python 3.10 or newer and the repository environment:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[research,test]"
```

The HyRAM-dependent consequence adapter is optional. Install `.[all]` only in
an environment where the GPL-3.0 dependency is permitted.

## One-command integrity run

From the repository root:

```powershell
.venv\Scripts\python scripts\reproduce_ijhe.py `
  --run-focused-tests `
  --output tmp\ijhe_reproduction_report.json
```

The JSON report records the commit, interpreter, manuscript format result,
compiled-PDF hash checks, the bounded readiness decision and test output. The
default status is `SCIENTIFIC_GATES_OPEN` while any frozen external-validation
gate is unresolved. That status is expected during development and is distinct
from an integrity or software-test failure.

The latest checked-in reproduction record is
[`../research/ijhe_reproduction_run_2026_10_14.json`](../research/ijhe_reproduction_run_2026_10_14.json).
It contains the successful 24-page PDF build, audit-mirror comparison and
12-test paper-integrity focused run from source commit `841ade7`.

To make a release workflow fail unless the bounded paper gate is closed, add
`--require-bounded`. The command intentionally returns a non-zero code in that
case; it never changes the audit or its thresholds.

## Separate scientific audit

Regenerate the reviewer-facing audit only after changing evidence, a protocol,
or the manuscript:

```powershell
.venv\Scripts\python scripts\audit_ijhe_readiness.py
.venv\Scripts\python scripts\check_ijhe_manuscript.py
```

The audit is mirrored in [`ijhe_readiness_audit.json`](ijhe_readiness_audit.json)
and [`../research/ijhe_readiness_audit.json`](../research/ijhe_readiness_audit.json).
The two files must have the same decision snapshot; the reproduction entrypoint
checks this explicitly.

## Software checks

The focused set is the fast paper-integrity guard:

```powershell
.venv\Scripts\python -m pytest `
  tests/test_ijhe_readiness_audit.py `
  tests/test_ijhe_audit_snapshot_consistency.py `
  tests/test_ijhe_manuscript_format.py `
  tests/test_ijhe_compile_artifact.py `
  tests/test_goal_progress_snapshot.py `
  tests/test_ijhe_reproduction.py -q
```

Run the complete regression suite only after broad code changes:

```powershell
.venv\Scripts\python -m pytest -q
```

The last complete run is retained in
[`../research/full_regression_test_run_2026_10_11.json`](../research/full_regression_test_run_2026_10_11.json).
That record is historical evidence; it is not silently presented as a new run.
Use `--run-full-regression` when a fresh run is required.

## What a reviewer can and cannot infer

The route makes the exact source, PDF, audit snapshot, protocols, hashes and
software commands traceable. It does not prove field safety, operator
effectiveness, regulatory compliance or journal acceptance. The frozen audit
continues to report failed external-validation strata and the unavailable
synchronized station-to-vehicle raw holdout as limitations. Confidential KGS
station records remain outside the repository; only approved aggregate or
de-identified evidence may be published.
