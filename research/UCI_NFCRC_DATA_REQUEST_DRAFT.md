# UCI NFCRC HRS data request draft

This draft is for an investigator to send through the UCI NFCRC/California
Energy Commission data custodian. It is not an external request sent by this
repository.

## Purpose

Request a de-identified, independent validation trace for a hydrogen-refuelling
station digital-twin study. The requested data would be used only after a
pre-access protocol freeze and would be reported with provenance, quality flags,
licence terms and a cryptographic digest.

## Requested scope

For each complete vehicle or test-tank fill, please provide the original logger
export (CSV, Parquet or equivalent) with a common UTC or monotonic time base and
the following channels where available:

- vehicle/receptacle pressure and temperature;
- station-side dispenser pressure, temperature and mass flow;
- delivered mass or a calibrated mass-totalizer channel;
- storage-bank pressures and compressor state;
- nozzle/communications/protocol state and fill start/stop markers;
- ambient conditions, initial vehicle state of charge or pressure and tank
  capacity;
- sensor units, sampling intervals, calibration/uncertainty, quality flags and
  missing-value conventions.

Please identify whether the records include normal fills, interrupted fills,
back-to-back fills or fault/abort events, and provide the protocol version used
(for example SAE J2601/HGV 4.3) plus any pressure-ramp or temperature limits.

## Reuse and reproducibility

Please state the permitted licence or written reuse conditions, whether the
data may be redistributed as an immutable supplemental archive, and whether the
custodian can provide a DOI or persistent record. A de-identified subset is
acceptable if the selection rule and excluded channels are documented.

## Existing public artifact

The associated paper is DOI
[`10.1016/j.ijhydene.2020.08.251`](https://doi.org/10.1016/j.ijhydene.2020.08.251).
The public supplementary DOCX contains aggregate charts only; it does not
contain the synchronized raw traces required for independent full-loop scoring.

## Proposed evaluation safeguards

After access, the recipient would freeze the file digest, schema, inclusion
criteria and scoring metrics before viewing model results. No parameters would
be fitted on the requested holdout. Results would report pressure/temperature/
mass-flow errors, event timing, missingness, protocol adherence and failure
modes, with the data owner acknowledged and any redistribution restrictions
preserved.
