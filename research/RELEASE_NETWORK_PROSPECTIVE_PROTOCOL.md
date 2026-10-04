# Apparatus-resolved release model: prospective validation protocol

This protocol defines a future validation of the separate development model in
`src/h2station/release_network.py`. It is not a replacement for the frozen
Schefer, Proust, PRESLHY or Grune results, and it does not convert those
consumed results into validation evidence.

## Model boundary

The model contains two finite control volumes: a source vessel and a supply
line. A time-dependent valve opening fraction connects the source to the line;
the line discharges through a terminal restriction to ambient. Each volume
has a gas mass and internal-energy state. Optional lumped wall states exchange
heat with the gas and ambient; internal gas/wall area and external
wall/ambient area are separate geometry inputs. The model returns source and
line pressures,
temperatures, inventories, upstream flow and terminal flow on one clock.

No fitted discharge coefficient, opening time, line volume, time shift or
case-specific initial condition is permitted after a holdout outcome is read.
The geometry and valve law must be frozen from an apparatus drawing,
calibration record or an independent data-custodian statement before the
numerical archive is opened.

## Required raw channels

An eligible release campaign must contain a common timestamp for source
pressure/temperature, line or manifold pressure/temperature when available,
terminal mass flow or transferred mass, valve command or measured valve
position, ambient pressure/temperature and the source/line geometry. Units,
sampling rules, calibration uncertainty, missing-value codes and the physical
location of each channel must be supplied by the custodian.

The primary screens are fixed before access: peak-normalized mass-flow NRMSE,
median absolute percentage error above ten percent of peak, pressure NRMSE and
half-peak or half-pressure time when the measured crossing is observable. The
case is the unit for any aggregate pass fraction and bootstrap interval. Every
eligible case and every numerical failure is retained.

## Admission and split

At least eight untouched cases are required, spanning at least two source
pressures, two restriction or line-geometry groups and two valve-opening
conditions. The source digest, case manifest, model commit, thresholds and
split are recorded before numerical values are inspected. A station or vessel
trace lacking a declared line/valve boundary may support a bounded diagnostic
only; it cannot enter the primary apparatus-resolved claim.

## Current status

The repository contains the implementation and unit tests for mass closure and
finite valve/line states. No qualifying new raw campaign has been received and
no result from this model is used in the IJHE readiness audit. The full-loop
and consequence gates therefore remain unchanged.
