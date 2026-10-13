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
geometry inputs. Gas-to-wall transfer can use either the legacy constant
coefficient or the state-dependent Churchill--Chu natural-convection
correlation. The latter uses local HEOS hydrogen properties, wall-gas
temperature difference, and separately declared source/line characteristic
lengths. The model returns source state, the complete line pressure,
temperature and inventory profiles, every boundary flow, valve position,
cumulative terminal mass and enthalpy, net thermal-boundary energy, and
instantaneous mass/energy conservation residuals on one clock. It also returns
the source and line heat-transfer-coefficient histories so the thermal boundary
is auditable rather than hidden.

The number of line volumes is a physical topology declaration, not a numerical
mesh refinement control. A multi-volume run is admissible only when the volume
and equivalent restriction at every boundary can be frozen from apparatus
information. The one-line-volume default preserves the original candidate.

No fitted discharge coefficient, opening time, line volume, heat-transfer mode,
characteristic length, time shift or case-specific initial condition is
permitted after a holdout outcome is read. The topology, geometry, valve law,
thermal areas and characteristic lengths must be frozen from an apparatus
drawing, calibration record or an independent data-custodian statement before
the numerical archive is opened.

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

## Executable holdout path

`research/apparatus_release_holdout_manifest.template.json` is the private
campaign-manifest template. The custodian replaces its example geometry with
as-built or independently calibrated values, assigns anonymous case aliases,
records each raw CSV SHA-256, and freezes the completed manifest before running
the model. The synchronized CSV contract uses explicit SI-unit headers; the
evaluator rejects missing or non-finite channels, duplicate timestamps,
excessive timestamp jitter, an unmatched valve trajectory, an inconsistent
initial mass, or a boundary variation that the constant-ambient model cannot
represent.

Run the frozen campaign once with:

```text
python scripts/run_apparatus_release_holdout.py \
  --manifest <private-frozen-manifest.json> \
  --output <aggregate-result.json>
```

The result retains all declared cases and numerical errors, but contains no raw
rows, source paths, facility identity, exact dates or manufacturer details.
The completed manifest and logger files stay outside the public repository.
The archived result contains only anonymous aliases, hashes, metrics and the
bounded decision. A failed result is preserved and cannot be converted into a
development set under the same model version.

## Current status

The repository contains the implementation and unit tests for mass and
open-system energy closure, finite valve travel, resolved line pressure and
inventory gradients, reverse inter-volume flow, separate thermal areas and
state-dependent natural convection. Constant mode reproduces the earlier
candidate trajectory. The multi-volume and thermal revisions were introduced
before any qualifying target campaign was received. They are prospective
candidate revisions, not repairs of an inspected holdout. No result from this
model is used in the IJHE readiness audit. The full-loop and consequence gates
remain unchanged.
