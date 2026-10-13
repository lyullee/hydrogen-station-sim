# High-pressure release-flow sensitivity contract

## Runtime behavior

The configured release calculation remains the point estimate.  No runtime
discharge coefficient is fitted from validation outcomes.  Free-orifice
results now carry a second, explicit model-and-public-experiment sensitivity
range.  A line-flow-limited release preserves its process cap and is not
widened using terminal-orifice evidence.

## Public evidence

### HyTunnel-CS actual-hydrogen blowdown

- Dataset DOI `10.23642/USN.14405903`, article DOI
  `10.3390/en14113008`, CC BY 4.0.
- Five synchronized actual-hydrogen blowdowns through the exact 0.5 mm nozzle
  family, using the same one-second aggregation and eligibility rule as the
  frozen holdout.
- Observed source domain: 1.6845--71.4655 MPa absolute and
  262.1307--296.0777 K.
- Frozen primary result: 3/5 cases passed the prespecified mass-flow screen;
  the unchanged $C_d=0.8$ model underpredicted all five measured peaks by
  approximately 18--20%.
- Post-outcome diagnostic central union: effective coefficient
  1.0041--1.1310, formed from the minimum case q10 and maximum case q90.

For an exact 0.5 mm free orifice, the runtime envelope spans the unchanged
point estimate and this central sensitivity range. It is marked
`PUBLIC_ACTUAL_HYDROGEN_ENVELOPE_IN_DOMAIN` only inside the observed pressure
and temperature domain. No diameter interpolation is made between HyTunnel
and the unrelated Proust campaign.

### Proust terminal-orifice campaign

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

The Proust runtime envelope spans the unchanged point estimate and the aperture-wise
P10--P90 diagnostic.  Between 1 and 3 mm it linearly interpolates the two
diagnostic limits.  Outside the experiment's aperture, pressure, or
temperature domain it is marked `PUBLIC_EXPERIMENT_ENVELOPE_EXTRAPOLATED`.

## Claim boundary

This is a sensitivity range derived from digitised public mass-flow curves.
It is not a statistical confidence interval, a fitted site coefficient, a
measured station release, a consequence-distance validation, or a separation
or evacuation distance.  The failed single-coefficient holdout remains a
retained negative result.

The HyTunnel range is likewise post-outcome. It does not change $C_d=0.8$,
rewrite the frozen 3/5 result, or establish station leak, source depletion,
dispersion, thermal, overpressure, detector, control, or safety-distance
validity. Its purpose is to expose the measured underprediction risk beside
the operational point estimate.

Machine-readable source diagnostics:

- `research/proust_release_holdout_result.json`
- `research/proust_discharge_coefficient_sensitivity_2026_10_06.json`
- `research/hytunnel_carpark_holdout_result_2026_10_08.json`
- `research/hytunnel_carpark_effective_cd_diagnostic_2026_10_12.json`
