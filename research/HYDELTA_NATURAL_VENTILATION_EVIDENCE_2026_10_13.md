# HyDelta natural-ventilation evidence audit

- Status: **verified_report_level_natural_ventilation_evidence**
- DOI: <https://doi.org/10.5281/zenodo.8164602>
- License: `CC BY 4.0`
- Actual-hydrogen cabinet cases transcribed: `10`
- H70 runtime calibration: **false**
- Bounded empirical cabinet screen: **enabled**

## Decision-support finding

The controlled cabinet experiments show that natural or enlarged ventilation can reduce hydrogen accumulation, but it does not by itself prove that a cabinet is below the 4 vol% hydrogen LFL. Hydrogen accumulated preferentially near the top, and some enlarged top-plus-bottom ventilation configurations still permitted flammable mixtures. Operator guidance must therefore require a gas measurement before opening or declaring the area safe.

## Bounded facts exposed to SAGA

- Upper hydrogen blanket reported: `True`
- Ventilation alone proves safe state: `false`
- Maximum tabulated inside concentration: `24.0 vol% H2`
- Smallest indicative mini-cabinet flow with a flammable reading: `0.125 Nm3/h H2`

## Runtime empirical screen

The runtime now replays an exact measured row or returns the two adjacent
measured rows for the exact `0.5 m3` and `4.0 m3` cabinet families. The input
mass flow is converted to `Nm3/h` only to select those rows. Concentrations are
not interpolated, cabinet volumes are not interpolated, and flows outside
`0.125–5.8 Nm3/h` are explicitly marked outside the public domain. The
indicative mini-cabinet cases are retained as qualitative context and are not
used numerically.

The empirical result is carried beside the normal consequence result and into
the compact LLM evidence envelope. It never overwrites the HyRAM concentration,
pressure, heat-flux, or distance output. Every result keeps the source DOI,
license, measured bracket, the requirement for independent gas clearance, and
an explicit `safety_clearance_authorized=false` field.

## Claim boundary

> The CC BY 4.0 report provides actual-hydrogen, cabinet-scale measured concentration evidence for ventilation and response wording. The values are report tables rather than machine-readable time series, the mini-cabinet tests are explicitly indicative, and the geometries are low-pressure gas distribution cabinets. They do not validate the H70 station dispersion proxy, detector placement, alarm thresholds, ESD effectiveness, release rate, or site separation distance.
