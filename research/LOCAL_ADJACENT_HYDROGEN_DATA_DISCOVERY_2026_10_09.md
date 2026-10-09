# Local adjacent hydrogen-process data discovery (2026-10-09)

The local workspace contains substantially more hydrogen-process material than
the station telemetry bundle already used for station-side calibration. This
record keeps only aggregate structure. It deliberately omits source paths,
filenames, headers, identifiers, absolute dates, site/company/manufacturer
information, and measurement values.

## Aggregate result

- A high-pressure hydrogen-process collection contains **18 CSV event logs**
  with **2,411,774 rows**. The largest log has **2,410,985 rows**.
- The event log contains **490 entity keys** and **273 logical keys**. The
  keyword screen finds pressure, temperature, flow-like and state-like value
  families, but their units, tag meanings, boundary roles and provenance are
  not attested.
- All rows in that event log are numeric value records. The accompanying local
  project index documents the time field as millisecond Unix epoch with KST
  conversion. The rows are interleaved across entities and keys; the structural
  scan found 11,059 negative *global* time steps, so a per-entity/key ordered
  replay is still required before treating it as a chronological trace.
- The local data dictionary contains hydrogen/fuel-cell pressure, temperature
  and flow-like keys. This confirms useful process context, but it classifies
  the collection as hydrogen-city/pipeline or fuel-cell operations rather than
  an H70 station-to-vehicle fill dataset.
- The same collection has **19 workbooks**, **69 sheets** and **64
  non-trivial tables**. These are reference/engineering candidates until a
  custodian confirms the measurement semantics.
- A separate liquid-hydrogen-centre collection contains **3 CSV files with 52
  scenario rows**, plus **17 workbooks with 78 sheets** (31 non-trivial
  tables). This is useful for qualitative operating and response sequences,
  not a gaseous H70 station-to-vehicle trace.
- A privacy-bounded discovery scan across the selected adjacent collections
  screened **122 machine-readable files** and **21 CSV/TSV headers**. It found
  keyword/header candidates, but **zero attested full-loop candidates**.

## Allowed use now

These collections can support process-context review, HAZOP/action mapping,
virtual valve/ESD sequence training, and a future adjacent-process diagnostic
after per-channel units, clock semantics, roles and reuse rights are attested.
They must not automatically change HRS runtime parameters.

They do **not** yet support a claim of synchronized station-to-dispenser-
vehicle validation, delivered-mass/SOC accuracy, incident frequency, safety
limits, or consequence-distance accuracy. The existing measured station bundle
remains the source for the station-side chronological holdouts.

The machine-readable aggregate is
[`local_adjacent_hydrogen_data_discovery_2026_10_09.json`](local_adjacent_hydrogen_data_discovery_2026_10_09.json).
