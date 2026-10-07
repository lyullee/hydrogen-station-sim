# Controlled multi-source full-loop intake

Use this procedure only when a controlled Excel workbook contains station and
vehicle signals in separate worksheets with a confirmed common time basis. The
source file, worksheet names, original labels, timestamps, values, mapping,
and attestation remain outside the repository and must not be committed.

The same exporter also accepts a controlled directory containing explicitly
mapped CSV, XLSX, or XLSM sources. For a directory, each source declaration
must add a relative `file` field; CSV sources may omit `worksheet`. The
directory is not searched or joined implicitly, and paths outside it are
rejected.

This is stricter than merely finding related labels in one workbook. Before
export, the data custodian must confirm that the selected worksheets describe
the same event, their clocks are compatible, every mapped numeric field is in
the canonical unit, and each discrete state has a written meaning.

## Create a private mapping workbench

For a new controlled CSV/XLSX/XLSM source or a directory of explicitly mapped
sources, create editable private templates first. The command keeps original
worksheet names, relative source files, and headers only in the
outside-repository output folder. It does not retain measurement values.

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\prepare_controlled_multisource_intake.py `
  --input "D:\controlled\event.xlsx" `
  --output-directory "D:\controlled\mapping-workbench"
```

The workbench contains `private_source_catalog.json`,
`event-mapping.template.json`, and `event-attestation.template.json`. Replace
each placeholder after a custodian verifies the event, units, state meanings,
and clocks. These files contain original labels and must remain controlled.

## Private mapping contract

Create a private mapping JSON beside the controlled workbook. Every required
station-to-vehicle field must occur exactly once across `sources`; a source may
contribute only the fields it owns. `header_row` is explicit so title rows are
never guessed.
The sole supported joining method is nearest observation within the declared
maximum offset. It does not interpolate measurements or infer missing values.

Time alignment is not evidence that two source tables describe the same fill or
fault. Each source in a mapping must therefore carry the identical private
`event_group_token`, and the custodian must separately attest
`same_physical_event_confirmed: true`. The exporter checks token equality but
never writes the token to a de-identified trace, receipt, manifest, or public
repository artifact. Do not join convenient signals from different runs merely
because their clocks can be aligned.

```json
{
  "schema_version": 1,
  "sources": [
    {
      "file": "<relative source file when --input is a directory>",
      "worksheet": "<private vehicle sheet>",
      "header_row": 1,
      "event_group_token": "<same opaque private token for all sources in this event>",
      "time_column": "<private time label>",
      "time_format": "%Y-%m-%d %H:%M:%S",
      "column_map": {
        "vehicle_pressure_mpa_abs": "<private pressure label>",
        "temperature_degC": "<private temperature label>",
        "mass_flow_g_s": "<private mass-flow label>"
      }
    },
    {
      "file": "<relative source file when --input is a directory>",
      "worksheet": "<private station sheet>",
      "header_row": 1,
      "event_group_token": "<same opaque private token for all sources in this event>",
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

For a cascade-resolved evaluation, add all three fields below (possibly from a
separate, synchronised storage worksheet) and attest each as `MPa_abs`. Do not
map only one or two of them:

```json
{
  "cascade_low_pressure_mpa_abs": "<private low-bank pressure label>",
  "cascade_medium_pressure_mpa_abs": "<private medium-bank pressure label>",
  "cascade_high_pressure_mpa_abs": "<private high-bank pressure label>"
}
```

When none of these three channels is available, the exporter produces a
station-to-vehicle partial-cascade bundle. It cannot be used to assess
cascade-bank dispatch or recharge dynamics, and missing bank pressures must
not be inferred or interpolated.

The existing private attestation must additionally include:

```json
{
  "source_synchronization": {
    "common_time_basis_confirmed": true,
    "same_physical_event_confirmed": true,
    "alignment_method": "nearest_observation"
  }
}
```

## Declare what each temperature actually measures

The vehicle-temperature channel must not be assumed to be a gas temperature
just because its unit is °C. In the private attestation, declare one of
`gas_temperature`, `liner_temperature`, `shell_temperature`, or
`sensor_weighted_tank_temperature` for `vehicle_temperature_degC`, and declare
`delivered_gas_temperature` for `delivered_gas_temperature_degC`. For both,
the custodian must confirm the sensor location, measurement/averaging method,
and calibration or traceability status. These free-text details stay in the
private attestation; a de-identified export retains only the coarse observation
operator.

This guards against the specific error of comparing a measured tank-wall or
sensor-average temperature directly with a simulated gas temperature. It does
not itself validate the observation operator or the thermal model.

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

## Screen the clocks before reading measurement channels

After the header preflight passes, run the clock-only preflight before the
full export. It uses the custodian-approved event mapping and declared maximum
offset, but evaluates only the selected time column from each source. Its
receipt contains anonymous source indexes and offset summaries; it contains no
worksheet names, original labels, measurement values, or absolute timestamps.

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\export_confidential_multisource_full_loop_bundle.py `
  --input "D:\controlled\event.xlsx" `
  --mapping "D:\controlled\event-mapping.json" `
  --attestation "D:\controlled\event-attestation.json" `
  --alignment-preflight
```

Proceed only when this command returns exit code `0` and reports
`ready_for_controlled_export: true`. An exit code of `2` with
`time_alignment_outside_declared_tolerance` means the selected clocks cannot
be joined under the declared rule. Correct the controlled event selection or
its documented synchronization; do not increase the tolerance simply to make
the report pass. This is a data-admissibility check only and does not evaluate
process, vehicle, safety, or model outcomes.

A successful receipt makes the trace eligible for the frozen evaluator, but
does not demonstrate model accuracy or scientific readiness.
