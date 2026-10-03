# NREL HITRF controlled-data request draft

**Purpose.** Request a de-identified, reproducible subset of Hydrogen Infrastructure
Testing and Research Facility (HITRF) records for independent validation of the
hydrogen-station digital twin. This draft is a technical request template only; it
does not claim that NREL has agreed to provide data.

## Requested release

Please provide a minimally sufficient set of complete fills, including successful
normal fills and clearly labelled interruptions or faults where publication is
permitted. A preferred release is one file per fill plus a machine-readable data
dictionary and a manifest. CSV, Parquet or XLSX are acceptable if timestamps and
units are preserved.

Required common-time-base channels, where available:

- station-side source and cascade-bank pressure, temperature, inventory or valve state;
- dispenser inlet/outlet pressure, gas temperature, precooler outlet temperature,
  mass flow and cumulative transferred mass;
- vehicle/receptacle pressure, gas temperature or tank temperature and estimated SOC;
- nozzle/receptacle connection, start/stop, abort, vent and safety-interlock events;
- compressor, chiller and control-mode states;
- alarm, ESD and maintenance/fault codes with event timestamps;
- ambient temperature and any available wind/ventilation context.

For every channel, request the tag name, engineering unit, sampling interval, time
zone/reference clock, calibration or uncertainty information, missing-value code,
quality flag and any signal filtering or resampling already applied.

## Protocol and provenance

For each fill, please include the target pressure class (H35/H70 or other), protocol
version (SAE J2601/MC Formula or internal research protocol), precooling target,
initial pressures and temperatures, vehicle/tank configuration, nozzle and hose
configuration, source-pressure boundary, and the reason for termination. A manifest
should include the original file digest, de-identification steps, export date,
station/facility identifier, and any known sensor or clock changes.

## Reuse and publication terms

The request should ask whether derived metrics and anonymized plots may be published
in an IJHE submission, whether the data may be redistributed or only inspected under
a data-use agreement, and whether a blinded holdout can be supplied. No raw file will
be committed to this repository without explicit permission. If access is controlled,
we will record the agreement, hash the received files, freeze the scoring protocol
before evaluation, and publish only permitted derived results.

## Pre-registered evaluation

Before opening any outcome column, freeze the model version, protocol settings,
metrics and pass thresholds. The planned primary checks are pressure RMSE/MAE, gas
or tank-temperature RMSE/MAE, transferred-mass or SOC error, stop-reason agreement,
and event-order agreement. Report every case, including failures, with confidence
intervals and a case-level audit trail. Component-only or endpoint-only tables will
be reported as contextual evidence and will not be promoted to full-loop validation.

## Current evidence boundary

The public [NREL HITRF description](https://www.nrel.gov/hydrogen/hitrf-animation?print=)
confirms an integrated, instrumented research station and automated data logging.
The NREL-hosted IJHE sample-fill table is useful for endpoint face-validity, but the
underlying synchronized station-to-vehicle logger is not publicly released. This
request is therefore a path to independent validation, not evidence that the gate
has already passed.
