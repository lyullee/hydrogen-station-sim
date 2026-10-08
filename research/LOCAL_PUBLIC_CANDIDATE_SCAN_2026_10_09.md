# Local public candidate scan (2026-10-09)

The local public-validation corpus was screened with
`scripts/scan_local_workspace_candidates.py`. The scanner retains aggregate
counts only; it does not publish paths, filenames, headers, values or rows.

## Result

- 263 machine-readable files were enumerated.
- 159 CSV/TSV headers were screened successfully.
- 58 candidates were classified as release-rig or jet experiments.
- 2 candidates mentioned vehicle/dispenser terms but were static QRA result tables without a synchronized time series.
- No candidate met the discovery contract for a synchronized vehicle pressure,
  vehicle temperature and flow/mass trace on a common time axis.

The scanner deliberately requires a time field and a flow/mass field before it
classifies a vehicle pressure-temperature candidate. This prevents static
results such as dispenser overpressure tables from being mistaken for measured
fueling telemetry. The result is still a discovery screen: units, boundary
roles, initial conditions, provenance and reuse rights require dataset-specific
review before a prospective validation split.

The public corpus remains useful for tank/refueling components, release, fire,
dispersion, detector and ventilation validation. The complete station-to-
vehicle full-loop gate remains closed.
