# Public full-loop search recheck — 2026-10-10

The targeted recheck did not identify a new, untouched, rights-cleared raw
station-to-vehicle fueling archive that satisfies the frozen full-loop gate.
The sources were still useful, but their roles are narrower:

- NREL H2FillS is a thermodynamic simulation tool and interface reference.
- SAE J2601 provides protocol scope and process limits.
- IPCEI and H2-Stations provide station inventory or availability context.
- The NLR/Kuroki vehicle-tank fueling paper reports real experimental boundary
  conditions, but its data-availability statement says the research data are
  not shared, so it cannot supply a rights-cleared raw holdout.

None of those sources supplies the synchronized station/dispenser pressure,
delivered-gas temperature, receiving-vessel boundary, mass transfer and
protocol-state trace required for the independent holdout.

The repository therefore continues to use public experiments, accident
precedents, field benchmarks and station-side private diagnostics for the
claims they support. The full-loop gate remains open until at least three
privacy-safe events are received and frozen before outcome access.

The machine-readable classification is in
`research/public_full_loop_search_recheck_2026_10_10.json`. It contains no
local paths, raw rows, site identity, company identity or equipment identity.
