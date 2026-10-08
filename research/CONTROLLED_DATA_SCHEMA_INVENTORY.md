# Controlled data schema inventory

This intake command locates a likely schema row within the first 40 rows of
controlled CSV, XLSX, XLSM, and ZIP-contained tables. This accommodates title rows in logger
exports. It never retains or discloses source file names, worksheet names,
headers, values, timestamps, equipment identities, or locations. The short
schema-search window is not used for calibration or outcome assessment.

The receipt reports generic semantic coverage such as time, pressure,
temperature, mass flow, vehicle, cascade/storage, compressor, dispenser, and
controller-state channels. A `full_loop_candidate` is only a header-level
candidate within one table. A `co_located_full_loop_candidate` means that
separate tables in one workbook or archive have complementary channel labels;
it is a cue for custodian review, **not** evidence that the tables share a
clock or can be joined. Neither result has passed channel mapping,
unit/calibration attestation, source synchronization, protocol freezing,
quality screening, or an untouched holdout evaluation.

For flat CSV exports, the inventory also reports two clock diagnostics. The
legacy `flat_time_axis_candidate_summary` compares bounded clock *shape* and
can therefore join equal-duration files from different dates. The stricter
`time_overlap_candidate_summary` separates explicit absolute clocks from
relative clocks. Absolute-clock tables must overlap for at least 80% of the
shorter bounded interval and have compatible cadence; relative-clock tables
must have an identical bounded fingerprint. Maximal pairwise-compatible groups
prevent a long historian file from transitively merging unrelated events.

Path text may contribute equipment-context hints only (for example, vehicle or
storage). Those hints are reported separately as unattested, never assign a
measured quantity or unit, and never promote a candidate to validation.
Aggregate missing-family histograms are safe to publish; file names, headers,
absolute timestamps, fingerprints and measurements remain private.

Run the command in a controlled environment and save its aggregate JSON report
outside this repository:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\audit_controlled_data_schema.py `
  --input-root "D:\controlled\owner-data" `
  --input-root "D:\controlled\public-data" `
  --output "D:\controlled\review\hrs_schema_inventory.json"
```

The output deliberately contains no per-file result, source hash, original
header, sample value, date, or location. If it finds one or more
`full_loop_candidate` schemas, the next step is the controlled mapping and
attestation workflow in
[CONTROLLED_FULL_LOOP_XLSX_INTAKE.md](CONTROLLED_FULL_LOOP_XLSX_INTAKE.md),
not immediate model calibration.
