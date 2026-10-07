# MetHyTrucks Hy-SaM post-access external diagnostic

This record adds the highest-value public measurement set found in the latest
search: three synchronized workbooks from a physical ZBT hydrogen refuelling
station. The dataset is published under CC BY 4.0 as
[Group B -- HySam system measurement data](https://doi.org/10.5281/zenodo.20590842)
and accompanies the 2026 Clean Technologies article
[Representative Hydrogen Sampling at Hydrogen Refuelling Stations](https://doi.org/10.3390/cleantechnol8030091).

## Result

The raw files were kept outside Git and verified against three committed
SHA-256 values. All workbooks use a common 0.5 s sampling interval. Integrating
the flow-like `QT_D02` channel reproduces changes in the cumulative-mass-like
`FWg35_Masse` channel, supporting the inferred mass boundary. The largest active
session in Test 9 transferred 2.329 kg by flow integration versus a 2.170 kg
scale change, a ratio of 1.073.

The already-frozen public Type-IV tank model was replayed without case-specific
fitting. Under the explicitly provisional channel interpretation documented in
the JSON result, pressure RMSE was **1.293 MPa** and temperature RMSE was
**6.071 degC** over 201.5 s. Final pressure was overpredicted by 4.020 MPa and
peak temperature by 7.210 degC. These errors are reported as observed; they
were not used to retune the model.

## Claim boundary

This is a **post-access external component diagnostic**. Numerical outcomes
were inspected before the diagnostic protocol was written, and the public
release does not include a channel dictionary, a test-to-device crosswalk,
sensor calibration/uncertainty metadata, controller state or storage-bank
selection tags. The result therefore does not close the prospective full-loop
validation gate, establish SAE J2601 conformance or support a field-safety
claim.

The candidate mapping is retained as an auditable hypothesis:

- `PT01`: sink/tank pressure, interpreted as bar absolute;
- mean of `TT08` through `TT11`: sink/tank temperature in degC;
- `QT_D02`: hydrogen mass flow in g/s after the measured idle baseline;
- `TEX01`: delivered-gas temperature in degC;
- `PTD10`: upstream/dispenser pressure in bar absolute;
- sink volume: 0.244 m3 from the accompanying article's Hy-SaM setup 1.

## Highest-value next action

Obtain the publisher channel dictionary and workbook-to-device crosswalk, then
freeze the mapping before replaying a disjoint, previously uninspected logger
event. A full-loop test also requires controller, bank-selection and valve-state
channels. Until those are available, the authoritative status remains a useful
independent-laboratory transfer diagnostic with an open full-loop gate.

The machine-readable record is
[`methytrucks_hysam_postaccess_diagnostic_2026_10_08.json`](methytrucks_hysam_postaccess_diagnostic_2026_10_08.json).
