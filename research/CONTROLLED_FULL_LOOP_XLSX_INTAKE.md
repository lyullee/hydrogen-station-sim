# Controlled full-loop CSV/Excel intake

This procedure lets a custodian prepare a station-to-vehicle validation event
without copying raw records, original column names, station identity, exact
timestamps, or equipment identifiers into the repository.

It supports CSV, XLSX, and XLSM input.  A CSV mapping may declare `encoding`
and `delimiter`.  An Excel mapping must declare the exact `worksheet` name;
the tool never guesses a worksheet.  The mapping and the attestation must stay
outside this repository with the source file.

## 1. Freeze the mapping before reading rows

Create a private mapping JSON.  The placeholder values below must be replaced
locally with the custodian-approved source headers and must never be committed.

```json
{
  "schema_version": 1,
  "worksheet": "<approved worksheet name>",
  "column_map": {
    "time_s": "<private time column>",
    "vehicle_pressure_mpa_abs": "<private vehicle pressure column>",
    "temperature_degC": "<private tank or gas temperature column>",
    "mass_flow_g_s": "<private mass-flow column>",
    "station_pressure_mpa_abs": "<private station pressure column>",
    "delivered_gas_temperature_degC": "<private delivery-temperature column>",
    "cascade_source_pressure_mpa_abs": "<private cascade pressure column>",
    "cascade_selected_bank": "<private state column>",
    "compressor_state": "<private state column>",
    "precooler_state": "<private state column>",
    "leak_check_state": "<private state column>",
    "vent_state": "<private state column>",
    "fault_state": "<private state column>",
    "esd_state": "<private state column>"
  }
}
```

For CSV, omit `worksheet` and optionally add `encoding` and `delimiter`.  The
canonical numeric units are absolute MPa, degrees Celsius, and g/s.  Convert
units before the mapping is frozen; the exporter does not infer gauge pressure
or scale factors.

Create the separate private attestation using the fields required by
`scripts/export_confidential_full_loop_bundle.py`.  It must confirm controlled
research authorization, the unit of each numeric role, every discrete-state
meaning, calibration/quality metadata, and `outcomes_accessed_before_protocol_freeze: false`.

## 2. Run a header-only preflight

This command reads the mapping, attestation, and source header only.  It does
not read measurement rows or print original headers, worksheet names, row
counts, identities, or timestamps.

Its result records SHA-256 values of the private mapping, attestation, and
frozen protocol.  The later controlled receipt additionally records the
source-file digest.  These hashes are reproducibility anchors; they do not
contain source labels or measured values and must remain with the controlled
evaluation record rather than being added to this repository.

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\export_confidential_full_loop_bundle.py `
  --input "D:\controlled-data\event.xlsx" `
  --mapping "D:\controlled-data\event-mapping.json" `
  --attestation "D:\controlled-data\event-attestation.json" `
  --preflight
```

Only proceed when `ready_for_controlled_export` is `true`.  If a canonical
channel is reported missing, correct the private mapping or record the event as
ineligible.  Do not substitute, interpolate, or invent the missing channel.

## 3. Export a controlled, de-identified event

Choose a new empty directory outside the repository.  The generated bundle
contains only relative time and generic canonical fields.  It deliberately
does not retain the original source filename, header labels, absolute time, or
station identity.

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\export_confidential_full_loop_bundle.py `
  --input "D:\controlled-data\event.xlsx" `
  --mapping "D:\controlled-data\event-mapping.json" `
  --attestation "D:\controlled-data\event-attestation.json" `
  --output-directory "D:\controlled-data\exports\event-001"
```

The exporter then runs the existing frozen manifest and trace-quality screens.
A successful receipt means that one de-identified trace has the required
channel contract and time-base quality for a later evaluator.  It does **not**
show model accuracy, safety distance, safety certification, or journal
readiness.  Preserve failed and ineligible events alongside eligible ones for
the later fixed-scoring evaluation.
