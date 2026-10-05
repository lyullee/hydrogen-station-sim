# Confidential authorized-channel contract

This contract records how owner-controlled station traces may contribute to
the digital-twin replay. It is a publication-safe description; raw files,
source column names, timestamps, site identity, and equipment identifiers are
not included.

## Boundary rule

- The documented station pressure boundary is the only role authorized by
  default.
- A station-level temperature may be used only when the custodian attests the
  generic role, unit conversion, calibration status, and synchronized overlap.
- An equipment temperature, flow, valve state, or lifecycle channel remains
  diagnostic by default. It can affect a replay boundary only after its exact
  generic role is placed in `TraceMapping.authorized_boundary_roles` and, for
  an equipment temperature, `temperature_boundary_role` identifies the same
  role.
- A mapped channel is never promoted because its source name looks like a
  pressure, temperature, or flow tag.

## Data-use boundary

The calibration code may publish aggregate pressure statistics, timing quality,
state-transition counts, and approved derived margins. It does not persist raw
rows, absolute timestamps, source paths, source tag names, or operator/site
identifiers. Boundary fitting is performed on a pre-declared calibration slice;
later holdout outcomes are not used to choose parameters.

## Enforcement

`h2station.controlled_station_replay.TraceMapping` defaults to
`authorized_boundary_roles=("station_pressure",)`. The adapter rejects an
equipment boundary temperature without an explicit role attestation, and
unattested temperatures remain available only as in-memory diagnostic values.
The private mapping file supplied by the data custodian is the authorization
record; this public document does not disclose that mapping.

## Claim boundary

This contract strengthens provenance and prevents accidental channel leakage.
It does not turn a partial station-boundary replay into an independent
station-to-vehicle validation. That claim still requires synchronized vehicle,
dispenser, mass-flow, and pressure/temperature channels with fixed holdout
scoring and a reviewer-access path when the raw data cannot be public.
