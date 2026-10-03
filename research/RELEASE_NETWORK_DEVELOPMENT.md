# Release-network development diagnostic

This is **consumed development evidence**, not confirmatory validation. The
Proust outcomes had already been used to select the equivalent restriction, and
the Imamura numeric arrays had been viewed before this comparison was
formalized. The prospective Proust result remains negative and unchanged.

## Question

Can one fixed series restriction explain the diameter-dependent error seen in
the independent Proust 90 MPa release campaign, and does that restriction carry
over to a different apparatus?

The diagnostic combines a terminal-orifice conductance and an equivalent
upstream conductance as

`C_eff = 1 / sqrt(1 / C_nozzle^2 + 1 / C_supply^2)`.

The post-outcome Proust selection used nozzle `Cd = 0.91`, supply `Cd = 0.8`
and an equivalent supply diameter of `2.62 mm`. These values are fitted
apparatus descriptors; they are prohibited as validation parameters.

## Results

Using the same descriptive 15% peak-normalized RMSE and 20% median-error
reference screens:

| Dataset/model | Diameter | NRMSE | Median error | Within reference screen |
|---|---:|---:|---:|---:|
| Proust, selected series restriction | 1 mm | 11.75% | 15.92% | yes |
| Proust, selected series restriction | 2 mm | 12.01% | 9.84% | yes |
| Proust, selected series restriction | 3 mm | 7.40% | 15.82% | yes |
| Imamura, selected Proust restriction | 1 mm | 3.63% | 3.22% | yes |
| Imamura, selected Proust restriction | 2 mm | 13.24% | 19.20% | yes |
| Imamura, selected Proust restriction | 3 mm | 29.25% | 44.06% | no |
| Imamura, selected Proust restriction | 4 mm | 41.81% | 63.60% | no |
| Imamura, direct aperture `Cd = 1.0` | 1 mm | 4.44% | 7.80% | yes |
| Imamura, direct aperture `Cd = 1.0` | 2 mm | 3.79% | 6.53% | yes |
| Imamura, direct aperture `Cd = 1.0` | 3 mm | 5.91% | 10.38% | yes |
| Imamura, direct aperture `Cd = 1.0` | 4 mm | 7.60% | 13.34% | yes |

## Interpretation and decision

The series restriction can describe the already-consumed Proust curves, but it
underpredicts the larger Imamura releases severely. A plain nominal-aperture
model performs better across the consumed Imamura series. The 2.62 mm value is
therefore evidence of Proust apparatus-specific valve or upstream resistance,
not a universal correction to hydrogen nozzle flow.

The next source model must represent documented valve geometry, pipe inventory
and wall heat transfer explicitly. Its coefficients must be locked before
opening the numerical outcomes of another facility-level campaign. No
confirmatory claim, safety-distance claim or controller claim follows from this
diagnostic.

Machine-readable results, source hashes and the contamination disclosure are in
`research/release_network_development.json`.
