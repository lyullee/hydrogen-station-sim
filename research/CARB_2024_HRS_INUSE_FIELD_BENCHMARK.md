# CARB 2024 in-use HRS field benchmark

## Why this evidence matters

The California Air Resources Board (CARB) tested 22 operating light-duty
hydrogen stations with a HyStEP device and an abbreviated CSA/ANSI HGV 4.3:22
matrix. The study directly tests whether deployed station controls respond to
SAE J2601 process, fault and communication conditions. It is therefore a much
stronger functional-relevance benchmark than a design-only reference.

This repository uses the report as a **field benchmark and feature-gap audit**.
It does not use the aggregate results to tune the pressure, temperature, flow
or consequence models. The report does not publish synchronized
station-dispenser-vehicle raw traces.

## Main observations

- 22 of about 55 operating stations were tested.
- None passed every HGV 4.3 test in the abbreviated matrix.
- Five passed all fault and communication tests.
- Four passed all nine evaluated fueling-performance metrics.
- Reported category pass rates were 45.5% for general fault, 40.9% for protocol
  fault, 50.0% for communication and 18.2% for fueling performance.
- At in-use testing, 16 stations used an MC-formula protocol and six used a
  table-based protocol.

The transcribed machine-readable counts are in
[`carb_2024_hrs_inuse_field_benchmark_2026_10_08.json`](carb_2024_hrs_inuse_field_benchmark_2026_10_08.json).
Each result tuple is ordered as `pass, fail, undetermined` and cites the report
page and table.

## Immediate digital-twin implications

The current runtime already represents configurable vehicle capacity and
initial pressure, pressure/SOC targets, maximum flow, maximum vehicle gas
temperature, delivery-temperature boundaries, operator stop and ESD.

The field benchmark identified communication faults as the first high-value
gap. The runtime now supports dispenser-specific Abort, Halt, data-loss,
invalid-CRC and invalid-value injection with conservative fill termination.
The remaining high-value behavior is:

1. maximum-startup-mass and minimum-startup-time conformance checks;
2. upper/lower pressure-corridor evaluation;
3. protocol-selectable non-communication fallback and resumed fueling;
4. explicit T30/T40 conformance reporting.

These gaps are feature-coverage findings. Closing them will improve training
and controller testing, but will not create external dynamic-model validation
without independent time-series measurements.

## Reproduction

```powershell
.\.venv\Scripts\python.exe scripts\build_carb_hrs_inuse_benchmark.py `
  --source-pdf C:\path\to\carb_2024_hrs_in_use_report.pdf
```

The builder checks the PDF against the pinned SHA-256 before generating the
artifact. The public PDF is referenced rather than copied into this repository.

Source: [CARB, *Existing Light-Duty Hydrogen Refueling Stations In-Use Study Report* (2024)](https://ww2.arb.ca.gov/sites/default/files/2024-12/Existing%20Light-Duty%20Hydrogen%20Refueling%20Stations%20In-Use%20Study%20Report%20ADA%20AL.pdf).
