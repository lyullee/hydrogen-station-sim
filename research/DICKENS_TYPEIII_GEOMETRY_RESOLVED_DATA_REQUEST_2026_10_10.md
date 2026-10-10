# Dickens Type-III geometry-resolved data request (draft)

This is a prepared request only. No message has been sent and no new outcome
trace has been treated as available. The purpose is to obtain one fresh or
source-held untouched Type-III filling trace so the model can be evaluated
without turning a post-outcome sensitivity into a validation claim.

## Minimum request

Please provide one of the following:

1. a new filling trace that is not in the already inspected HydDown archive;
2. an explicitly identified untouched holdout split retained by the data
   custodian; or
3. a custodian-run evaluation package in which the numerical outcomes are
   produced only after the attached protocol and model hash are frozen.

The minimum synchronized channels are:

- elapsed time from fill start;
- measured inlet mass flow or cumulative delivered mass;
- co-located inlet pressure;
- **time-resolved inlet hydrogen temperature**;
- tank pressure;
- mean gas temperature (or a documented equivalent measurement);
- ambient/enclosure temperature;
- initial gas, liner and shell temperatures;
- sampling interval, missing-data flags, calibration/uncertainty metadata and
  units.

## Geometry and boundary clarification

The published description identifies a 0.358 m internal diameter, a 5 mm
internal-diameter inlet pipe and 82 mm insertion. The available source mapping
also contains two different candidate tank lengths (0.893 m in the published
description and 0.7451 m in the archived case). Please confirm which physical
length belongs to the supplied trace and provide the associated internal volume
or the information needed to derive it. The length must be resolved from source
evidence before numerical outcomes are opened; it must not be selected by
minimizing model error.

## Rights and provenance

Please state the permitted use of the trace and derived aggregate metrics in an
academic paper and repository. The custodian may keep the raw file and return a
hash-locked, de-identified export or a custodian-run result. We do not need
names, addresses, serial numbers or exact calendar dates. A random event alias
and elapsed-time axis are sufficient.

The model, parameter values, acceptance screens and holdout rule are frozen in
`research/dickens_typeiii_geometry_resolved_prospective_protocol_2026_10_10.json`.
No case-specific fitting, smoothing, dynamic time warping, time shifting,
selective case removal or outcome-dependent geometry choice will be used.

## Suggested message

> We are preparing an independent, unfitted evaluation of a layered hydrogen
> Type-III tank-filling model. Could you provide one fresh filling trace or an
> explicitly untouched holdout with elapsed time, inlet mass flow, co-located
> inlet pressure and time-resolved inlet hydrogen temperature, tank pressure,
> mean gas temperature, ambient temperature, initial conditions, units and
> quality flags? Please also confirm the physical tank length associated with
> the trace and the permitted use of aggregate results. The model and scoring
> protocol will be hash-frozen before numerical outcomes are opened, and all
> failures will be retained.

## Current status

Until a qualifying trace and rights statement are received, this remains a
pre-access request. The original Dickens prospective result remains a negative
result, and the post-outcome 5 mm diagnostic remains development evidence only.
