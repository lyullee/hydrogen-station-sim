# NBSDC HRS operational data request draft (2026-10-09)

This is a request draft for the public catalogue record **Operational Data List of Hydrogen Refueling Stations for Beijing Winter Olympics** (CSTR `16666.11.nbsdc.aI3fJrzX`). It is not a data-access attempt and does not bypass the catalogue's approval requirement.

## Requested scope

Please provide a de-identified research extract, or confirm which fields can be released, for the four listed materials:

1. transaction records;
2. hydrogen refueling-gun records;
3. compressor records; and
4. the data-description document and channel dictionary.

The minimum useful extract is a synchronized station-side trace. If a receiving vehicle or receiving vessel boundary is present, it should be included as a separate pseudonymous event stream. Site name, company identifiers, exact calendar dates, vehicle identifiers, operator names and manufacturer serial numbers can be removed or coarsened.

## Required metadata for reproducible validation

For every released file or table, please provide:

- a pseudonymous event/run identifier and a common monotonic time base;
- engineering units, sampling interval, missing-value convention and timezone handling;
- pressure, temperature, flow or transferred-mass channel definitions;
- compressor, storage-bank, valve, dispenser and protocol/state signals where available;
- initial conditions, nominal storage/vehicle capacity class and pressure class;
- sensor calibration or stated measurement uncertainty;
- the meaning and provenance of normal, fault, leak, fire or emergency labels, if any;
- any clock offsets between transaction, gun and compressor files; and
- checksums and file version information.

## Rights and privacy conditions

Please state whether the extract may be used for:

- internal model calibration;
- an independent, pre-registered external holdout;
- publication of aggregate metrics and derived plots;
- redistribution of the raw files, or only release of derived aggregates; and
- citation of the CSTR record and data custodian.

The receiving project can accept a no-redistribution agreement and can publish only aggregated, time-shifted, de-identified results. Raw rows would remain outside the public repository unless explicit permission is granted.

## Pre-access protocol

Before opening any measurement values, the project will freeze the channel map, unit conversions, train/holdout split, scoring screens and exclusion rules. Files that lack a common clock, unit attestation, receiving-vessel mapping or reuse terms will remain a component or station-side diagnostic and will not be counted as full-loop validation.

## Acceptance decision after access

The data will be classified as one of:

- **full-loop holdout candidate** — station/dispenser and receiving-vessel/vehicle pressure, temperature and delivered mass/flow share a verified time base and controller/protocol state;
- **station-side holdout** — transaction, compressor, storage or dispenser-side dynamics are usable but the receiving boundary is absent or ambiguous; or
- **schema/context only** — metadata or aggregate information is available without a reproducible time-series trace.

This draft is stored for an approved custodian request. It does not claim that the catalogue files are currently accessible or that they will satisfy the full-loop gate.
