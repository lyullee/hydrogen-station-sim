# UCI early HRS supplementary recheck (2026-10-09)

The local public-validation cache contains the supplementary DOCX associated
with the early-years UCI hydrogen-refuelling-station study. It is a useful
aggregate operational reference, but it is not a raw synchronized logger
archive.

## Observed structure

- The document contains four embedded charts.
- One chart exposes 30 monthly points for refrigeration energy, compressor
  energy, auxiliary energy and dispensed hydrogen mass.
- The remaining charts are presentation-level comparisons/trend graphics; no
  machine-readable station-to-vehicle event table is embedded.

## Eligibility decision

The artifact supports aggregate energy and throughput plausibility checks and
can guide a future data-custodian request. It does not contain the common time
base, vehicle/receptacle pressure and temperature, dispenser flow, controller
state and delivered-mass fields needed for an independent station-to-vehicle
holdout. The full-loop gate remains closed.

The repository records only aggregate structure. The source document, exact
source path, site identity, dates and chart values are not copied into the
repository.
