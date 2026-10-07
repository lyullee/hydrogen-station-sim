# Consequence-Screening Validation Scope

## Purpose

Every sensor-based consequence result now carries its evidence boundary with
it.  The boundary is provided to the API, direct-answer views, and LLM evidence
manifest so a calculated display range cannot be recast as a field-verified
safe distance.

## What the runtime result supports

`COMPONENT_SCREENING_BOUNDED` identifies a model-based outdoor, unconfined
hydrogen free-jet screening result.  The result may report the threshold
crossings at configured observation points and the directional 4 vol% plume
centerline estimate.  Its display mapping has bounded component evidence:

- `research/hyram_adapter_verification.json` records production-adapter parity
  with the tested HyRAM+ 6.1 interface.
- `research/consequence_geometry_validation.json` records the independent
  outdoor free-jet plume, radiation, and overpressure display-mapping checks.

The result is therefore suitable for comparing simulated scenarios under the
same configured assumptions and for driving the training visualisation.

## What it does not support

The following flags remain false for every current consequence result:

- `source_depletion_external_holdout_supported`
- `full_station_vehicle_validation_supported`
- `site_specific_safety_distance_supported`

In particular, the frozen external station-to-vehicle holdout recorded in
`data/public_validation/results/closed_loop_external_holdout/validation.json`
did not pass its predeclared screens.  It is retained as a disclosed negative
result, not used to tune the runtime calculation and not hidden from the LLM
claim boundary.

A displayed thermal/overpressure threshold crossing is an observation-point
screening value.  It is not a site separation distance, evacuation boundary,
regulatory determination, or safety certification.

## Data protection

This runtime context is static and only names public repository artifacts.  It
does not load measurement rows, equipment identifiers, timestamps, site names,
or private source mappings.  Restricted data can inform separately attested
station-boundary calibration, but cannot expand the consequence claim scope
without a predeclared, independent validation protocol.
