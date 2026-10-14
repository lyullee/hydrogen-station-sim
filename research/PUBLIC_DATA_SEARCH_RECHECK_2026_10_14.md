# Public data search recheck — 2026-10-14

This recheck searched for a new, rights-cleared experimental dataset that could close one of the remaining independent validation gates. It follows the same access-order rule as the frozen protocols: a source already opened for an outcome-informed diagnostic cannot be counted again as a new holdout.

## Findings

- The JRC GasTeF record describes a reference database and full-scale Type III/IV hydrogen filling experiments, but the public record does not expose a machine-readable pressure-temperature logger export. The papers and figures are useful boundary evidence only.
- The European H2-Stations API exposes station metadata, availability and related operational signals. It does not expose a synchronized process logger bundle with pressure, temperature and mass flow.
- The DTU-TES Hydrogen-Fuelling-Station repository is an open Modelica simulation library. It is useful for model comparison, but it is not an independent measured holdout.
- The California in-use report provides operational study figures, but no rights-cleared common-clock station/controller/vehicle raw bundle was found.
- A recent IJHE Type III/IV refueling study (DOI `10.1016/j.ijhydene.2026.156406`) was checked through the publisher/index records. It provides experimental and model summaries, but no accessible rights-cleared machine-readable pressure-temperature-time supplement or repository archive was found; it remains boundary evidence only.
- An ICHS 2011 full-scale garage release paper was also checked. It reports four sensor locations, response timing and plotted concentration histories for repeated hydrogen/forming-gas releases, but no machine-readable raw time series or explicit redistribution terms were found. Because the outcome was accessed after the frozen spatial protocol, it is retained as actual-hydrogen spatial-response boundary evidence only.
- H2SAFE, ELVHYS and the other public sources already in the repository remain governed by their existing frozen protocols. Reusing them as new holdouts would invalidate the access-order audit.
- The current National Laboratory of the Rockies H2SAFE catalog entry was checked again. It is the same five-case helium-surrogate cohort already used for candidate development, so the newer catalog presentation does not create an independent actual-hydrogen holdout.
- The official PRESLHY E3.5 record was checked as a possible new source. It describes 25 liquid-hydrogen release experiments and an 11.3 GB archive with pressure, mass-flow, temperature, concentration and weather channels. One workbook from that archive was already accessed before a new prospective protocol; the campaign also does not represent the gaseous HRS station-side or station-to-vehicle loop. It remains consequence-boundary evidence unless a separately unaccessed member can be frozen under a claim-limited protocol.

The machine-readable record is [public_data_search_recheck_2026_10_14.json](public_data_search_recheck_2026_10_14.json). No new eligible raw dataset was found, so the readiness gate counts and runtime model are unchanged. The next evidence-changing action is a rights-cleared, previously uninspected Type-III pressure-temperature trace or a new independent pressure-decay/release campaign, with the scoring protocol frozen before outcomes are opened.
