# Prospective protocol: ignited enclosure pressure peaking

This protocol freezes a component-level validation before the remaining raw
outcomes are downloaded or opened. The source is the public DataverseNO
dataset [10.23642/USN.17934047](https://doi.org/10.23642/USN.17934047), linked
to Lach and Gaathaug's large-scale ignited pressure-peaking study
([10.1016/j.ijhydene.2020.12.015](https://doi.org/10.1016/j.ijhydene.2020.12.015)).

## Frozen cohort

- Holdout: experiments **2–28** (`datafile_id` 266048–266074).
- Development-only: experiment **1**, opened during the prior inventory sample
  check, and experiments **29–31**, opened during the channel-integrity replay.
- Expected holdout count: 27. A file can be excluded only for an identity,
  channel, time-base, or finite-data failure defined in the JSON protocol.

## Fixed model and inputs

The model is a zero-dimensional, well-mixed reacting enclosure balance for
H2, O2, N2, and H2O with ideal-gas pressure, vent flow, reverse inflow during
underpressure, and a lumped steel-wall heat balance. It consumes each case's
measured non-negative hydrogen mass-flow trace. The common vent coefficient
`C = 0.9` and wall heat-transfer coefficient `h = 30 W/m²/K` are fixed from
the associated study and cannot be fitted per experiment.

The apparatus is fixed at 14.9 m³ (2.5 × 2.0 × 2.98 m), with a 4 mm vertical
release and immediate ignition. Documented passive vent areas are 0.0055,
0.0109, and 0.0164 m² for one, two, and three vents.

Signal processing is also frozen before holdout access. Initial temperature
is the mean of the four channel medians from 0.2–1.2 s. The same interval
provides the single pressure-baseline correction. Negative mass-flow samples
are clipped to zero, and the 10 kHz mass-flow channel is reduced to 500 Hz by
non-overlapping 20-sample means. Peaks are evaluated over 1–12 s. Trace NRMSE
uses the same interval at 100 Hz, with no time shift or outcome-dependent
filtering.

## Decision rule

The primary endpoint is absolute peak-overpressure error. A case passes at
**≤2.0 kPa**, matching the accuracy boundary reported by the source study.
Confirmatory success requires at least 20 eligible holdout cases and at least
80% passing the primary endpoint. Peak-time relative error and trace NRMSE are
secondary diagnostics and cannot rescue a failed primary result.

No parameter may be retuned after outcome access. A failed result remains in
the record; any revised model must be described as exploratory unless it is
tested under a newly frozen protocol against untouched evidence.

## Claim boundary

The result will apply only to ignited pressure peaking in a vented enclosure.
It cannot validate an outdoor H70 station fueling loop, jet-flame radiation
distance, emergency controls, operator response, or SAGA effectiveness.
