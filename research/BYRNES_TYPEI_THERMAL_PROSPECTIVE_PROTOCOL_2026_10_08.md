# Prospective Byrnes Type-I hydrogen thermal validation protocol

This protocol freezes three exact public HydDown `v0.50.0` validation files and
the local pressure-driven thermal model before their numerical validation
arrays are downloaded or opened. Public prose and file names were known; the
pressure and temperature coordinates were not.

The measured pressure is imposed as a boundary, so the experiment cannot be
used to infer a valve coefficient and then score its own pressure prediction.
The model predicts bulk gas temperature from a real-gas open-system energy
balance, a lumped wall and a fixed natural-convection correlation. Geometry and
wall properties may be read only from non-validation YAML sections. No
case-specific heat-transfer multiplier, time shift, channel substitution or
file replacement is allowed.

Each case is compared with the published upper/lower gas-temperature envelope.
A joint case pass requires envelope-miss RMSE at most 10 K, sensor-midpoint RMSE
at most 12 K, at least 80% coverage inside the sensor envelope expanded by 5 K,
and relative energy residual at most 1e-4. At least two of all three selected
cases must pass. Missing units or wall/geometry metadata produces a retained
ineligible result rather than an inferred input.

Any pass is limited to Type-I pressure-driven bulk thermal response. Pressure
prediction, valve and line flow, composite tanks, station control and accident
consequences remain outside this test.
