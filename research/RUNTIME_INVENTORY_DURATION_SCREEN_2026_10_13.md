# Runtime inventory/current-rate screen — 2026-10-13

## Purpose

The consequence view now reports how much modeled hydrogen inventory remains
above the ambient-pressure equilibrium mass and divides that inventory by the
current release-flow sensitivity bounds. This gives an operator a transparent
inventory scale while a release is active instead of showing consequence
intensity from an instantaneous flow alone.

## Calculation

For a component with modeled volume `V`, current inventory `m`, current gas
temperature `T`, and ambient pressure `p_amb`, the screen calculates

`m_releasable = max(0, m - rho_H2(p_amb, T) V)`.

The bank and vehicle inventory comes directly from the digital-twin state.
Where no explicit state inventory is published, density is evaluated from the
selected pressure and temperature sensors and the runtime component volume.
Runtime-configured component volumes take precedence over the static HAZOP
catalogue value.

If the public-experiment release-flow sensitivity interval is `[q_low,
q_high]`, the displayed constant-rate ratios are

`t_low = m_releasable / q_high` and `t_high = m_releasable / q_low`.

These ratios deliberately do not integrate pressure depletion, wall heat
transfer, valve closure, continued inflow, line pack, or detector response.

## Evidence and claim boundary

The flow sensitivity range retains the existing Proust et al. public release
evidence boundary (DOI `10.1016/j.ijhydene.2010.04.055`). The source-depletion
model still lacks a passing independent external holdout. The new values are
therefore labeled `CURRENT_RATE_RATIO_ONLY` in the API, LLM evidence manifest,
direct deterministic summary, and bilingual consequence card.

They are not a validated pressure-decay forecast, valve-isolation time,
evacuation time, blowdown completion time, leak-end time, or site safety
distance. SAGA is instructed to preserve that boundary when explaining them.

## Verification

The tests cover use of the exact live bank inventory, precedence of a
runtime-configured bank volume, ordering of the lower/upper current-rate
ratios, propagation through the compact LLM evidence envelope, and publication
of effective component volumes in live frames.
