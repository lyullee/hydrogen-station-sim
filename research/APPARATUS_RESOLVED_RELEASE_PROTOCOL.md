# Apparatus-resolved release protocol

This is a prospective protocol specification for the next rights-cleared
facility logger archive. It records the additional state needed to test a
source vessel, supply line, valve and terminal restriction as one physical
system. It does not alter the frozen Proust result and it is not an external
validation claim.

## Why the protocol is needed

The published Proust campaign describes a 25 L Type-IV source, a 10 m nominal
10 mm supply line, a short valve opening and 1–3 mm terminal restrictions. The
current public holdout evaluator observes source pressure/temperature and
weighing-derived flow, but models only a local terminal aperture. Its negative
diameter-dependent residual pattern therefore cannot distinguish a valve or
line-inventory effect from an aperture-model error. The new protocol makes that
distinction testable without fitting to the existing outcomes.

## Locked implementation

The candidate implementation is
`src/h2station/release_network.py`, SHA-256
`BE4D21BD0D5C52A20CDA6609D4D3CE1D349C576BB4498CF3ACF4A9DBAB856D42` after a
pre-access numerical-conservation instrumentation revision. It has source and
line mass/energy states, finite valve opening, terminal flow and optional wall
thermal states. It also reports cumulative terminal mass, cumulative terminal
enthalpy, thermal-boundary energy, and instantaneous mass/energy residuals;
these bookkeeping states do not feed the physical trajectory. It is
development-only and is not wired into the station runtime.

The nominal line dimensions imply 0.000785398 m³ of geometric internal volume
(`pi × 0.010² / 4 × 10`). That number is only a derivation from published
dimensions. An as-built bore, fittings and dead-volume measurement must replace
it before a confirmatory run.

## Required logger contract

Every confirmatory run must contain synchronized source pressure and
temperature, line pressure and temperature, terminal mass flow, valve position,
source mass and ambient pressure. Source/line/terminal channels must be sampled
at least 20/100/100 Hz respectively; valve position requires 500 Hz. The
published Proust record does not report the line and valve channels, so it is
retained as a local-aperture supplementary comparison rather than promoted to
this protocol.

Before opening numerical rows, freeze the as-built geometry, valve law,
discharge coefficients, heat-transfer terms, solver configuration, sensor
calibration, synchronization rule, missing-data rule, endpoints and archive
hash. No case-specific fitting, time shifting, outcome-driven cropping or
diameter-specific correction is allowed.

## Pre-registered screens

At least two of three independent complete runs must pass all of the following:

* source-pressure NRMSE ≤ 15%;
* terminal-flow NRMSE normalized by measured peak ≤ 15%;
* terminal-flow median absolute percentage error ≤ 20%;
* integrated source-to-line-to-terminal mass closure relative error ≤ 0.2%.
* open-system energy closure relative error ≤ 0.2%.

Missing required channels make a run ineligible; they do not become a pass by
imputation. Calibration and digitization uncertainty are reported separately
and propagated to intervals, but cannot override a failed primary endpoint.
The 2026-10-07 instrumentation update was made before a target-campaign
outcome archive was opened; it adds numerical rejection checks and does not
alter the source-line-valve trajectory equations.

The machine-readable record is
`research/apparatus_resolved_release_protocol.json`. Its explicit promotion
gate remains `NOT_ESTABLISHED`, so the IJHE readiness audit must continue to
report the unresolved external-validation blockers.
