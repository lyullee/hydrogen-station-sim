# MC capacity-geometry leave-one-case-out diagnostic

This is a post-outcome within-campaign development cross-validation. It is not an independent validation and does not change the runtime model.

## Result

- Held-out joint screen: **4/8** cases.
- Mean pressure RMSE: **1.902 MPa** (56.5% lower than the frozen baseline).
- Mean tank-temperature RMSE: **9.202 °C** (-1.7% change; negative means worse).
- Mean final SOC absolute error: **2.983 percentage points** (66.9% lower).

The geometry rule materially improves pressure and SOC transfer, but four cases still fail because the unresolved temperature boundary dominates the joint decision.

## Claim boundary

This is a leakage-controlled within-campaign development cross-validation. It may guide the next frozen candidate, but it does not validate a vehicle, station controller, dispenser, consequence model or field safety function.
