# Apparatus-resolved release model: prospective validation protocol

This protocol defines a future validation of the separate development model in
`src/h2station/release_network.py`. It is not a replacement for the frozen
Schefer, Proust, PRESLHY or Grune results, and it does not convert those
consumed results into validation evidence.

## Model boundary

The model contains a source vessel and one or more physically declared supply
line or manifold volumes. A finite valve-opening curve connects the source to
the first volume; declared equivalent restrictions connect adjacent volumes;
the last volume discharges through a terminal restriction to ambient. Adjacent
volumes can exchange flow in either direction. Every volume has a gas mass and
internal-energy state. Optional lumped wall states exchange heat with the gas
and ambient; internal gas/wall area and external wall/ambient area are separate
geometry inputs. The model returns source state, the complete line pressure,
temperature and inventory profiles, every boundary flow, valve position,
cumulative terminal mass and enthalpy, net thermal-boundary energy, and
instantaneous mass/energy conservation residuals on one clock.

The number of line volumes is a physical topology declaration, not a numerical
mesh refinement control. A multi-volume run is admissible only when the volume
and equivalent restriction at every boundary can be frozen from apparatus
information. The one-line-volume default preserves the original candidate.

No fitted discharge coefficient, opening time, line volume, time shift or
case-specific initial condition is permitted after a holdout outcome is read.
The topology, geometry and valve law must be frozen from an apparatus drawing,
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

The repository contains the implementation and unit tests for mass and
open-system energy closure, finite valve travel, resolved line pressure and
inventory gradients, reverse inter-volume flow, and separate thermal areas.
The multi-volume structure was introduced before any qualifying target campaign
was received. It is therefore a prospective candidate revision, not a repair of
an inspected holdout. No result from this model is used in the IJHE readiness
audit. The full-loop and consequence gates remain unchanged.
