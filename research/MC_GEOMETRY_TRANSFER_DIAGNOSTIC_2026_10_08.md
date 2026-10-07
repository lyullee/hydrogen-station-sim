# MC Default vehicle geometry-transfer diagnostic

The corrected `Pinlet`/`Tinlet_G` tank replay showed that the largest remaining
systematic error is negative final pressure and SOC. This diagnostic compares
three geometry rules that already existed before this analysis:

1. the frozen Tables Method effective-volume multiplier;
2. the unadjusted 0.122 m³ per 4.7 kg reference vessel;
3. capacity divided by the hydrogen density at 70 MPa and 15 °C.

All eight MC Default outcomes were already inspected. No rule is fitted or
selected, the runtime model is unchanged, and the frozen 0/8 result remains.

| Geometry rule | Joint passes / 8 | Pressure RMSE | Temperature RMSE | SOC RMSE | Mean absolute final SOC error |
|---|---:|---:|---:|---:|---:|
| Frozen Tables Method multiplier | 0 | 4.376 MPa | 9.052 °C | 5.583 %p | 9.017 %p |
| Unadjusted reference volume | 4 | 1.712 MPa | 9.143 °C | 2.918 %p | 4.714 %p |
| Capacity/EOS volume | 4 | 2.146 MPa | 9.214 °C | 2.011 %p | 2.860 %p |

The outcome-derived mass-closure calculation spans effective-volume ratios of
about 0.856–0.987 relative to the reference geometry. This is evidence that one
global volume correction does not transfer between vessel sets. Those derived
ratios must not be used to select a production model after outcome access.

The highest-value data requirement is now explicit: every new full-loop case
must declare the vehicle system's exact internal volume, number of vessels,
nominal working pressure and temperature-sensor location before its outcome is
opened. A capacity label alone is insufficient.
