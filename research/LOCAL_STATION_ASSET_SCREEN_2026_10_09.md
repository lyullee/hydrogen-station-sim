# Local station asset screen (2026-10-09)

The local search found substantially more station-related material than the original 33-file telemetry bundle. The new material is useful, but it belongs to different evidence classes and must not be treated as one synchronized validation set.

The largest station-side bundle remains the 4.749 GiB time-series collection: after duplicate exclusion it contains 56,854,143 rows for pressure-cycle, cascade-state and longitudinal trend work. Its custodian role mapping still attests zero vehicle/dispenser channels, so it cannot validate a vehicle fill or SOC on its own.

A separate local liquid-hydrogen operational bundle contains three scenario tables with 52 procedure rows. Every row has leak, fire, explosion and hazard-classification fields, and the tables cite KGS, KOSHA, NFPA, ASME, IEC, CGA and API families. This is strong input for HAZOP coverage and virtual response-command mapping. It is qualitative procedure evidence, not an incident or synchronized sensor dataset.

The same local bundle contains 10-cycle operation workbooks (21 sheets, 28,121 non-empty rows), 13 minute trend workbooks (39 sheets, 18,086 non-empty rows), a 10-sheet timestamp/differential-pressure workbook (6,740 non-empty rows), and an eight-sheet recovered storage workbook (94,389 non-empty rows). These can support sequence replay, trigger persistence and trend plausibility checks after unit/provenance review. The recovered workbooks must remain labelled as reconstructed trend evidence.

The search also found an engineering-reference bundle with 18 PDFs and four images for P&ID/GA, inspection and equipment context, plus a separate media bundle with 54 images and three videos for visual scale and camera-view matching. These are useful for de-identified topology and 3D placement, but they are not telemetry.

The result is therefore **not a lack of data**. The current blocker is evidence alignment: the local collection is rich on station-side dynamics, procedure/Hazard controls and asset context, while a single independently attested station-to-vehicle synchronized cohort with vehicle pressure/temperature, delivered mass or SOC is still missing. The artifact records the privacy-bounded counts and claim boundaries without publishing paths, filenames, tags, dates, site identity or raw rows.

See [`local_station_asset_screen_2026_10_09.json`](local_station_asset_screen_2026_10_09.json) for the machine-readable inventory.
