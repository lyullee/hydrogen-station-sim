# Controlled multi-source full-loop intake

Use this procedure only when a controlled Excel workbook contains station and
vehicle signals in separate worksheets with a confirmed common time basis. The
source file, worksheet names, original labels, timestamps, values, mapping,
and attestation remain outside the repository and must not be committed.

This is stricter than merely finding related labels in one workbook. Before
export, the data custodian must confirm that the selected worksheets describe
the same event, their clocks are compatible, every mapped numeric field is in
the canonical unit, and each discrete state has a written meaning.

## Private mapping contract

Create a private mapping JSON beside the controlled workbook. Every canonical
field must occur exactly once across `sources`; a source may contribute only
the fields it owns. `header_row` is explicit so title rows are never guessed.
The sole supported joining method is nearest observation within the declared
maximum offset. It does not interpolate measurements or infer missing values.

```json
{
  "schema_version": 1,
  "sources": [
    {
      "worksheet": "<private vehicle sheet>",
      "header_row": 1,
      "time_column": "<private time label>",
      "time_format": "%Y-%m-%d %H:%M:%S",
      "column_map": {
        "vehicle_pressure_mpa_abs": "<private pressure label>",
        "temperature_degC": "<private temperature label>",
        "mass_flow_g_s": "<private mass-flow label>"
      }
    },
    {
      "worksheet": "<private station sheet>",
      "header_row": 1,
      "time_column": "<private time label>",
      "column_map": {
        "station_pressure_mpa_abs": "<private pressure label>",
        "delivered_gas_temperature_degC": "<private temperature label>",
        "cascade_source_pressure_mpa_abs": "<private pressure label>",
        "cascade_selected_bank": "<private state label>",
        "compressor_state": "<private state label>",
        "precooler_state": "<private state label>",
        "leak_check_state": "<private state label>",
        "vent_state": "<private state label>",
        "fault_state": "<private state label>",
        "esd_state": "<private state label>"
      }
    }
  ],
  "alignment": {
    "method": "nearest_observation",
    "anchor_source": 0,
    "maximum_offset_s": 1.0
  }
}
```

The existing private attestation must additionally include:

```json
{
  "source_synchronization": {
    "common_time_basis_confirmed": true,
    "alignment_method": "nearest_observation"
  }
}
```

## Run first without rows

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\export_confidential_multisource_full_loop_bundle.py `
  --input "D:\controlled\event.xlsx" `
  --mapping "D:\controlled\event-mapping.json" `
  --attestation "D:\controlled\event-attestation.json" `
  --preflight
```

Proceed only after the preflight reports `ready_for_controlled_export: true`.
Then use a new empty controlled output directory. The export retains only
relative time and canonical field names; it never saves original metadata in
the repository. Its private receipt also reports anonymous per-source
time-alignment offsets (minimum, median, 95th percentile, maximum, and the
count near the declared tolerance). Review those statistics before using the
trace: a pass only means every matched row met the stated tolerance; it does
not prove that the declared common time basis is physically correct.

A successful receipt makes the trace eligible for the frozen evaluator, but
does not demonstrate model accuracy or scientific readiness.
