# Dickens Type-III source geometry mapping

## Decision

The published Dickens Type-III experiment resolves the previously unknown inlet
pipe diameter: **5 mm internal diameter**, with the pipe extending **82 mm into
the tank**. That value supports the existing 5 mm mixed-convection sensitivity
as a physically grounded follow-up case. It does not revise the frozen negative
validation result, because the source mapping was established after the
outcome and after the sensitivity cases had been inspected.

The original source describes a 0.358 m internal diameter and a 0.893 m inner
length. The archived HydDown case uses the same diameter but a 0.7451 m length
to represent the 74 L case. This length difference is recorded as an explicit
mapping mismatch and must be resolved before a new prospective run.

## Source evidence

- Original paper DOI: `10.1016/J.JPOWSOUR.2006.11.077`
- ICHS paper record: [Dicken and Mérida experiment PDF](https://conference.ing.unipi.it/ichs2009/images/stories/papers/238.pdf)
- Public HydDown description: [Type-III validation case](https://github.com/andr1976/HydDown/blob/main/Manual.md)

The source also measured the entering hydrogen temperature. The archived case
contains a mass-flow boundary and tank pressure/gas-temperature traces, but not
the time-resolved inlet-temperature trace. That boundary remains required for a
new frozen protocol.

## Status and claim boundary

| Item | Status |
|---|---|
| Published inlet diameter | 5 mm, source-confirmed |
| Published inlet extension | 82 mm, source-confirmed |
| Archived case inlet diameter | Not declared |
| Tank diameter | Matched at 0.358 m |
| Tank length | 0.893 m source vs 0.7451 m archived case; unresolved |
| Time-resolved inlet temperature | Measured in source, absent from archived case |
| Frozen validation decision | Unchanged: pressure passed, gas-temperature screens failed |
| Runtime parameter | Unchanged |

The corresponding machine-readable record is
`research/dickens_typeiii_source_geometry_mapping_2026_10_09.json`.
The frozen result remains in
`research/dickens_typeiii_prospective_result_2026_10_08.json`; the prior
mixed-convection sensitivity remains a post-outcome diagnostic only.

## Next prospective run

Before opening a new holdout, freeze the 5 mm inlet diameter, 82 mm extension,
the chosen tank-length interpretation, and the time-resolved inlet-temperature
source. A successful new component-level run can support the tank-filling
thermal submodel. It cannot by itself validate a complete station-to-vehicle
loop or consequence-distance and SAGA claims.
