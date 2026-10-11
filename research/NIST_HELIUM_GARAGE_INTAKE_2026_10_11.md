# NIST helium-garage archive intake (2026-10-11)

The NIST Technical Note 1694 archive was acquired from the public NIST link and
audited without changing the production model or any frozen validation result:

- source: [NIST TN 1694, DOI 10.6028/NIST.TN.1694](https://doi.org/10.6028/NIST.TN.1694)
- archive: `HeliumDispersionDataSets.zip`
- archive SHA-256: `fd1c8c6f7b21c092b69b5962f70020ffca6422eff34d21bbdd5cc14cbef0c993`
- archive size: 53,895,011 bytes
- workbooks: 18 (`3600`/`14400` s × `LC`/`LR`/`UC` vents × `SLV`/`SSV`/`ULV` release locations)
- channels: elapsed time, eight helium volume-fraction channels and differential pressure
- enclosure: 1.5 m × 1.5 m × 0.75 m reduced-scale garage
- nominal flow: 14.8 L/min for the one-hour release and 3.71 L/min for the four-hour release
- measured flow: 14.92 ± 0.15 L/min and 3.54 ± 0.06 L/min, respectively

All 18 workbooks passed the schema and integrity audit. The machine-readable
summary, per-file hashes, row counts and sample intervals are in
[`nist_helium_garage_2011_intake_2026_10_11.json`](nist_helium_garage_2011_intake_2026_10_11.json).
The audit is reproducible with:

```powershell
.venv\Scripts\python.exe scripts\audit_nist_helium_garage_intake.py
```

This archive is recorded as a **component candidate**, not a validation pass.
The experiments use helium as a nonflammable hydrogen surrogate, and the report
states that flow began 60 s after acquisition while the workbook time axis does
not carry a release-state channel or an unambiguous wall-clock crosswalk. The
archive was opened after the existing H2SAFE spatial protocol was frozen, so the
outcomes cannot be used to tune detector placement, concentration conversion,
alarm/trip thresholds, ESD, consequence radii or the digital-twin runtime.

The evidence can support a future, separately pre-registered reduced-scale
ventilation/spatial transport component study if a release-to-logger timing
crosswalk and an independent holdout are established. It cannot close the
synchronized station-to-vehicle full-loop gate or support a field-safety claim.
