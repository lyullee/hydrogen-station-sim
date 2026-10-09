# Full local DocuData discovery boundary (2026-10-09)

This is a second-pass header-only discovery over the broader local document
collection. It is intentionally separate from the measured station bundle and
the adjacent hydrogen-process inventory. It contains no raw rows, source
paths, filenames, headers, identifiers, site names or measurement values.

## Result

- **38,528** machine-readable files were screened, including **12,804
  CSV/TSV headers**.
- A broad keyword pass found **783 vehicle/dispenser-like header candidates**.
  This is a discovery count only; the candidates are distributed across LH2
  experiments, pipeline/energy-system material, component tests and derived
  outputs.
- A refined header screen over **13,050 CSV files** found **zero** files that
  simultaneously expose a time field plus pressure, temperature and flow/mass
  families under the declared conservative vocabulary.
- The broad scanner recorded **139 release-rig/jet candidates**, which remain
  consequence or component evidence rather than HRS fueling traces.
- The scanner therefore registers **zero eligible full-loop HRS cohorts**.

## Interpretation

The local archive is data-rich. The limiting issue is semantic and boundary
alignment: a candidate must be a measured, synchronized station/dispenser/
vehicle record with known units, initial conditions, controller/protocol state,
and reuse permission. Keyword matches, plot exports, LH2 transfer tests and
pipeline/fuel-cell operation logs cannot be promoted to that holdout without
those checks.

The machine-readable aggregate is
[`local_docudata_full_discovery_2026_10_09.json`](local_docudata_full_discovery_2026_10_09.json).
