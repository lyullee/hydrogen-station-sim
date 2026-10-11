# Validation-scope manifest verification — 2026-10-11

The repository now verifies the privacy-bounded validation split without
opening or exporting the confidential station CSV rows. The verifier checks:

- all privacy flags remain false;
- the owner-controlled data retain the episode/time-order split and frozen
  calibration/holdout counts;
- the public Type-IV component split remains 23 calibration, 12 holdout and
  one mass-closure exclusion;
- every referenced result artifact matches its SHA-256 digest; and
- the synchronized station-to-vehicle full-loop lane remains explicitly
  excluded and reported as a paper limitation.

Run:

```powershell
.venv\Scripts\python.exe scripts\verify_validation_scope_manifest.py
```

The machine-readable result is
`research/validation_scope_manifest_verification_2026_10_11.json`.

This is an integrity and scope audit. It does not publish private rows, turn a
same-site holdout into independent external validation, or establish full-loop
station-to-vehicle accuracy.
