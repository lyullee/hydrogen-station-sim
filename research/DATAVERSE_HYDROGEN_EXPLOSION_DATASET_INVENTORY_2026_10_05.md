# DataverseNO hydrogen explosion dataset inventory

Generated: `2026-10-04T20:11:21.166637+00:00`

This report fixes the public provenance and summary-workbook boundary. It is not a model-validation result.

## Public sources

| Dataset | DOI | License | Files | Trace groups | Summary identity |
|---|---|---|---:|---|---|
| [Replication dataset for: Large-Scale Hydrogen Explosion Experiments: Obstructed Releases in open atmosphere](https://dataverse.no/dataset.xhtml?persistentId=doi:10.18710/WSKBIJ) | `10.18710/WSKBIJ` | `CC0 1.0` | 59 | text_trace_files=52, csv_trace_files=0, video_or_archive_files=6, workbook_files=1 | **True** |
| [Replication data for: Laboratory-Scale Experiments on Ignited Hydrogen Jets: Flame Acceleration and Overpressure Analysis](https://dataverse.no/dataset.xhtml?persistentId=doi:10.18710/X044QK) | `10.18710/X044QK` | `CC0 1.0` | 47 | text_trace_files=1, csv_trace_files=39, video_or_archive_files=6, workbook_files=1 | **True** |

## Published summary coverage

### Replication dataset for: Large-Scale Hydrogen Explosion Experiments: Obstructed Releases in open atmosphere

- **summary_kind:** `published_experiment_summary`
- **experiment_count:** `51`
- **nozzle_diameter_mm_range:** `[4.8, 9.4]`
- **reservoir_pressure_bar_range:** `[0.36, 221.52]`
- **explosion_pressure_sensor_count:** `4`
- **explosion_pressure_kpa_range:** `[-10.39, 235.39]`
- **experiments_with_numeric_pressure_sensor:** `45`
- **rows_with_missing_explosion_pressure:** `12`
- Summary workbook contains pressure peaks by experiment; raw text traces and selected high-speed camera files are separate API files.
- The README states that mass-flow instrumentation was available for experiments 1-27 only and ambient weather was not documented.

### Replication data for: Laboratory-Scale Experiments on Ignited Hydrogen Jets: Flame Acceleration and Overpressure Analysis

- **summary_kind:** `published_experiment_summary`
- **experiment_count:** `40`
- **max_pressure_bar_range:** `[0.0, 97.3553237915039]`
- **max_mass_flow_kg_s_range:** `[0.0, 0.013603470288217068]`
- **average_pressure_bar_range:** `[0.0, 71.24088287353516]`
- **average_mass_flow_kg_s_range:** `[0.0, 0.009954497218132019]`
- **obstacle_distance_cm_range:** `[29.0, 54.0]`
- **commented_experiments:** `['did not ignited', 'did not ignited', 'no data', 'no data fra pressure sensors. Movie er uten 10% pretrigger', 'spark was not generated -> no ignition', 'did not ignited']`
- Workbook reports pressure and mass-flow summaries for 40 numbered experiments; CSV files contain the large raw traces.
- The README describes four high-frequency piezoelectric pressure sensors and an upstream pressure transmitter.

## Claim boundary

These CC0 datasets provide independent release, ignition, pressure and mass-flow evidence for consequence-component checks. They do not contain a synchronized gaseous H70 station-to-vehicle fueling loop, and this inventory does not perform a model comparison. They therefore cannot close the full-loop external-validation gate or establish SAGA effectiveness.

- Model comparison performed: **False**
- Numeric validation gate closed: **False**
- Full-loop external validation supported: **False**

Freeze a consequence-model protocol and inclusion criteria, then run the locked model against raw traces without changing parameters after reading outcomes.
