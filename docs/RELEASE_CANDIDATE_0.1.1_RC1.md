# hydrogen-station-sim 0.1.1-rc1

This is the reproducible release candidate for the current station-side hydrogen safety digital twin. It fixes the exact source commit, CI evidence, readiness ledger, and known scientific blockers in [the manifest](../research/release_candidate_manifest_2026_10_12.json).

## What is included

- station-side process, safety, HAZOP and SAGA direct-answer simulation;
- public-data validation runners and reproducibility artifacts;
- software regression and CI checks;
- bounded IJHE manuscript and technical documentation.

The latest CI run passed at commit `115ceaa`: [run 38576334925](https://github.com/lyullee/hydrogen-station-sim/actions/runs/38576334925).

## Evidence boundary

The readiness ledger currently records **135 PASS, 11 FAIL, and 6 PENDING** gates overall. The primary station-side scope records **134 PASS, 10 FAIL, and 1 PENDING** (92.4% closure). The software is therefore reproducible, but this candidate is not independently validated or publication-ready.

The open gates are listed in `research/ijhe_submission_blocker_matrix_2026_10_12.md` and in the manifest. In particular, the full synchronized station-to-vehicle raw-data claim remains outside the primary scope and is disclosed as a limitation.

## Reproduce the software checks

```powershell
python scripts/run_priority_focus.py --priority critical --output artifacts/priority-focus-local.json
pytest -q tests/test_release_candidate_manifest.py tests/test_current_documentation_status.py
```

The scientific screen is intentionally reported separately from software pass/fail because several independent raw-data holdouts are still unavailable or fail the frozen acceptance criteria.
