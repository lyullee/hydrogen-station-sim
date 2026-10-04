# HIAD casebook machine preflight (2026-10-05)

The 24-case HIAD holdout approval input passes structural preflight. The
report verifies the declared holdout split, case count, unique event IDs,
required incident context, provenance fields, and the fact that every human
review marker is still unresolved.

Evidence: `hiad_casebook_machine_preflight_2026_10_05.json`.

This is deliberately a **machine-only** result. It does not decide whether a
narrative contains hindsight action leakage, approve or rewrite a vignette,
freeze the casebook, establish an ethics determination, collect masked model
responses, or provide an expert effectiveness/safety outcome. Those gates must
be completed by the named coordinator, institution, and independent reviewers
under `HIAD_COORDINATOR_REVIEW_HANDOFF.md` and the locked study protocol.

## Reproduce

```powershell
.venv\Scripts\python.exe scripts\preflight_hiad_casebook.py
```

The script returns exit code `0` only when the machine checks pass. A passing
exit code must not be interpreted as permission to collect holdout responses.
