# USN/FFI concentration-channel detector-logic evidence

This record replays the digital twin's declared gas-detector rule against the
public USN/FFI open-ended rectangular-channel measurements. The source is the
CC BY 4.0 Figshare record [10.23642/usn.26117989.v2](https://doi.org/10.23642/usn.26117989.v2),
which contains 22 experiments and 29 time-resolved hydrogen concentration
channels per experiment.

The rule tested here is the same unit convention used by the runtime safety
configuration after conversion to volume percent: alarm at **1.0 vol% H₂**,
trip at **2.0 vol% H₂**, and **0.5 s** persistence. A run is reset when the
measured sample gap exceeds 1.5 times that record's median positive sampling
interval. Detection time is the first observed sample completing the declared
persistence period.

## Result

The frozen replay produced:

| Measure | Result |
|---|---:|
| Experiments | 22 |
| Concentration channels per experiment | 29 |
| Experiments with at least one alarm detection | 22/22 |
| Experiments with at least one trip detection | 22/22 |
| Mean sensor coverage at alarm threshold | 0.887 |
| Mean sensor coverage at trip threshold | 0.809 |
| Median first alarm after filling start | 10.675 s |
| Median first trip after filling start | 10.675 s |

The machine-readable, case- and sensor-level output is
[`dispersion_detector_logic_validation.json`](dispersion_detector_logic_validation.json).
It includes the archive names, byte sizes and SHA-256 values used for the
replay, the exact thresholds, per-sensor detection times, and the claim
boundary.

## What this supports

This is evidence that the implementation deterministically applies its
threshold, persistence and missing-sample reset rules to measured hydrogen
concentration channels. It also gives a reproducible detector-coverage and
latency benchmark for the simulated safety logic.

It does **not** validate an outdoor hydrogen-refuelling station detector, its
response time, placement, calibration, ventilation, ESD effectiveness, or the
station pressure/flow model. The experiments use an open-ended rectangular
channel and concentration probes; they are a bounded detector-logic and
consequence-sensing evidence track, not an independent full-loop HRS holdout.
The existing full-loop validation gate therefore remains unchanged.

## Reproduction

With the raw Figshare archives present under
`data/public_validation/raw/hydrogen_dispersion_channel`:

```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python.exe scripts/run_dispersion_detector_validation.py `
  --output research/dispersion_detector_logic_validation.json
```

The unit tests for the persistence and threshold behavior are in
`tests/test_public_validation.py`.
