# De-identified HRS full-loop data request

This template requests a small, custodian-controlled pilot before any larger
release. It is intentionally written so that no site, company, manufacturer,
serial number or calendar date needs to be disclosed to the repository.

## Subject

Request for a three-event de-identified hydrogen-refuelling station-to-vehicle
trace pilot

## Message

Dear data custodian,

We are preparing an independently scored, claim-bounded validation of a
hydrogen-refuelling-station digital-twin model. We would like to request a
small pilot export of **three complete refuelling events** under your existing
data-governance process. The raw rows may remain under your control; a
custodian-run evaluation or a de-identified export is acceptable.

For each event, please provide (or attest that you can provide) the following
channels on a common elapsed-time clock:

* dispenser or hose pressure;
* vehicle or receptacle pressure and, if available, vehicle/receptacle
  temperature;
* delivered-gas or boundary temperature;
* mass flow or cumulative transferred mass;
* protocol phase and start/stop state;
* selected cascade/source bank, compressor/precooler state, and ESD/fault
  transitions when available.

Please also provide the engineering units, sampling interval, missing-value
convention, calibration/uncertainty summary, initial conditions, tank volume or
geometry class, and the event-level file hash. Relative elapsed time is
preferred; absolute timestamps are not required.

For every mapped channel, please include a short role attestation rather than
requiring the research team to infer semantics from tag names. At minimum this
should identify the generic role (for example `station_pressure_medium`,
`receiving_vessel_pressure`, `receiving_vessel_temperature`, or
`compressor_state`), engineering unit and scale/offset, and the missing-value
code. For discrete state channels, list the values that mean **active**,
**inactive**, **fault**, and **unknown**. For pressure channels, identify the
low/medium/high bank role or explicitly state that the bank role is unknown.
Please confirm that the role map and common-clock alignment were attested by a
custodian before the numerical rows are opened; a header-name guess is not
accepted as validation evidence.

The evaluation protocol and scoring code will be frozen before any numerical
outcomes are opened. No parameter fitting, smoothing, time warping or case
replacement will be performed on the pilot. We will return only aggregate
event-level diagnostics and a reviewer hash. Raw rows, site identity and
equipment identifiers need not be redistributed.

If three events are not immediately available, a single schema pilot or a
custodian-run score is still useful. Please identify which required role groups
are present and which are absent; we will not describe a station-side or
component trace as full station-to-vehicle validation.

Could you advise whether this request can be handled through an existing data
use agreement, secure review environment or technical-validation contact?

Sincerely,

[research team and institutional contact]

## Routes prepared in this repository

* [GTI station-evaluation report](https://www.osti.gov/biblio/1824631)
* [NREL NFCTEC](https://www.nrel.gov/hydrogen/nfctec)
* [Full-loop request package](FULL_LOOP_RAW_DATA_REQUEST_PACKAGE_2026_10_05.md)

## Claim boundary

This is a request template, not evidence of access, validation, safety
distance, SAGA effectiveness or journal acceptance. The full-loop gate remains
closed until a frozen, role-attested station-to-vehicle cohort is scored.
