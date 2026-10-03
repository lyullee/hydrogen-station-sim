# Independent 90 MPa release holdout result

The prospectively frozen Proust--Jamois--Studer evaluation is **eligible and
negative**. It does not support the high-pressure direct-aperture mass-flow
claim.

## Primary decision

- Eligible series: 3/3 required nozzle groups (1, 2 and 3 mm)
- Joint primary passes: 0/3
- 1 mm: 13 states, NRMSE 16.27%, median absolute percentage error 25.07%
- 2 mm: 10 states, NRMSE 16.01%, median absolute percentage error 15.85%
- 3 mm: 12 states, NRMSE 32.62%, median absolute percentage error 32.88%
- Frozen screens: NRMSE at most 15% and median error at most 20%
- Claim supported: **False**

The source PDF was acquired only after protocol commit `3fb8b91`. Figure 5 was
digitized independently from its PDF vector paths and from a 4x raster render;
Table 1 supplied measured temperature at the same reservoir-pressure states.
Only states inside the frozen 220--330 K and 2--95 MPa windows entered the
primary result. The PDF itself is not redistributed.

## Interpretation

The fixed coefficient 0.8 direct-aperture model underpredicted the 1 mm series
but increasingly overpredicted the 2 and 3 mm series. Post-outcome descriptive
least-squares effective coefficients were 1.141, 0.657 and 0.533,
respectively. These values are diagnostics only and are prohibited as fitted
validation parameters. Their strong diameter dependence is consistent with
unmodelled system resistance, effective-orifice differences, and the 10 m
supply line becoming material as terminal area increases.

Treating the plotted reservoir pressure as gauge and adding 101.325 kPa did not
change any pass/fail decision. All three digitization-uncertainty coverage
fractions were zero, so graph-reading resolution does not explain the failure.

## Claim boundary

This result concerns local gaseous-hydrogen mass flow inferred from published
pressure, temperature and mass-flow curves. It does not validate vessel-wall
depletion, pipe inventory, flame length, radiation, dispersion, station safety
distance, or fuelling control. A revised network source model may use this
dataset only as consumed development evidence and requires a new prospective
holdout.
