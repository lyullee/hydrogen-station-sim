# PRESLHY blowdown-validation protocol

Frozen: **2026-10-03**, before any numerical Excel outcome file in the
PRESLHY archive was opened.

## Pre-outcome amendment

Before any numerical Excel outcome was opened, the synchronization rule in the
initial freeze commit `b7cfd76` was corrected. PRESLHY D3.4 section 5.1 defines
published synchronized `t = 0` as the first significant `Pnoz` increase, not
the earlier valve-relay transition. This correction is recorded in the JSON
protocol amendment history and does not use model-performance information.

The same pre-outcome amendment history fixes the remaining input rules. An
explicit pressure-basis label controls when available. Otherwise a terminal
median from -0.5 to 0.5 bar is treated as gauge and receives a 1.01325 bar
ambient offset; a terminal median from 0.5 to 1.5 bar is treated as absolute;
other cases are excluded as ambiguous. A post-release increase must exceed
0.3125 bar before it counts toward the 10% increasing-sample exclusion. This is
0.125% of the report's 250 bar pressure-sensor full scale. Pressure strata are
fixed at <=20, >20 to <=100, and >100 bar absolute. The 10,000 case bootstrap
uses seed 20261003.

The parser, evaluator and runner were implemented and SHA-256 locked in the
JSON protocol before numerical workbook access. Eligible cases that encounter
a model/integration error are retained as primary-screen failures; they are not
converted into data exclusions.

A second pre-outcome code review corrected two implementation details without
changing the primary screens: measured ambient pressure in `cH2-Amb` is used
when available, and the secondary peak-flow value is calculated from accepted
integration states rather than rejected solver trial states. Revision 2 hashes
are the operative validation implementation.

## Purpose

This experiment evaluates the safety twin's source depletion and hydrogen
release physics against the public PRESLHY E3.1 DisCha tests. The facility used
a 2.815 L pressure vessel, 0.5, 1, 2 and 4 mm circular apertures, initial
pressures from 5 to 200 bar, and ambient- and cryogenic-temperature hydrogen.
The primary experiment uses only the ambient-temperature (`300K_DATA`) files.

The test is deliberately separate from the vehicle-fueling validation. A good
result would support an ambient, direct-aperture blowdown claim. It would not
validate a station vent stack, pipe backpressure, cryogenic two-phase flow,
ignition, dispersion or the controller/cascade/precooler fueling loop.

## Frozen model

The evaluated implementation is commit
`d5eb663d7c48d93e29ecf83601175d8b16e3eeaf`. The production property table,
restriction model, dynamic leak bridge and rigid-vessel inventory files are
hash-locked in `preslhy_blowdown_validation_protocol.json`. The discharge
coefficient is the existing value of 0.8. Neither global nor case-specific
fitting is allowed.

For each experiment, the model starts from measured vessel pressure and the
median available internal gas temperature immediately before valve opening.
It uses the published 2.815 L volume and nominal aperture. The rigid adiabatic
control volume loses the calculated discharge mass and its upstream specific
enthalpy. Prediction is linearly interpolated to measurement time; dynamic time
warping and optimized time shifts are prohibited.

## Outcome-independent eligibility

An experiment must come from a `PRE3P1A_KIT_D*_300K_DATA.zip` numerical package,
contain a synchronized valve-opening marker and at least 20 valid post-opening
vessel-pressure samples. The published synchronized time is used directly: its
zero is the first significant pressure increase in the release line (`Pnoz`),
not the earlier valve-relay transition. Missing/non-finite signals, acquisition
failure, sensor saturation, or a predominantly increasing post-release pressure
trace are exclusions. Model error is never an exclusion reason.

At least 12 cases spanning three aperture groups and three initial-pressure
groups are required. All eligible failures remain in the result.

## Primary decision

A case passes only if both conditions hold:

1. pressure NRMSE is at most 10% of initial absolute pressure; and
2. relative error in time to 50% of initial gauge pressure is at most 20%.

The aggregate claim requires at least 70% joint case passes. Case-level
bootstrap confidence intervals use 10,000 resamples. Pressure RMSE/MAE,
calculated peak flow, released mass and temperature error are reported as
secondary results. Balance-derived mass cannot overturn the primary pressure
decision because the source report describes its precision as limited.

A fixed sensitivity at discharge coefficients 0.7 and 0.9 may describe model
form uncertainty. It cannot change the primary result at 0.8.

## Acquisition status

The public metadata and technical report were inspected. The 1,313,122,304-byte
TAR advertises MD5 `b4d245866b7daed5705a06415a83b013` and CC BY 4.0. The
repository's HTTPS endpoint was intermittent during protocol preparation. No
numerical Excel outcome file was opened before freeze.
