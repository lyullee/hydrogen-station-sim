# High-pressure release-flow sensitivity contract

## Runtime behavior

The configured release calculation remains the point estimate.  No runtime
discharge coefficient is fitted from validation outcomes.  Free-orifice
results now carry a second, explicit model-and-public-experiment sensitivity
range.  A line-flow-limited release preserves its process cap and is not
widened using terminal-orifice evidence.

## Public evidence

- Proust, Jamois and Studer, *High pressure hydrogen fires*, DOI
  `10.1016/j.ijhydene.2010.04.055`.
- Independent 25 L Type-IV source, nominal 1--3 mm terminal apertures,
  approximately 10--90 MPa states.
- Frozen point model: real-gas isentropic aperture relation with global
  discharge coefficient 0.8.
- Frozen primary result: 0/3 diameter series passed both numerical screens.
- Post-outcome diagnostic: effective coefficient P10--P90 differs materially
  by nominal aperture (1 mm: 1.022--1.178; 2 mm: 0.619--0.747; 3 mm:
  0.497--0.653).

The runtime envelope spans the unchanged point estimate and the aperture-wise
P10--P90 diagnostic.  Between 1 and 3 mm it linearly interpolates the two
diagnostic limits.  Outside the experiment's aperture, pressure, or
temperature domain it is marked `PUBLIC_EXPERIMENT_ENVELOPE_EXTRAPOLATED`.

## Claim boundary

This is a sensitivity range derived from digitised public mass-flow curves.
It is not a statistical confidence interval, a fitted site coefficient, a
measured station release, a consequence-distance validation, or a separation
or evacuation distance.  The failed single-coefficient holdout remains a
retained negative result.

Machine-readable source diagnostics:

- `research/proust_release_holdout_result.json`
- `research/proust_discharge_coefficient_sensitivity_2026_10_06.json`
