# Prospective Byrnes Type-I hydrogen thermal validation protocol

This attempted protocol froze three exact public HydDown `v0.50.0` validation
files and the local pressure-driven thermal model. After the freeze, the
repository audit found that the same three YAML files and numerical outcomes
had already been accessed through Zenodo DOI `10.5281/zenodo.20728325` and are
recorded in `research/byrnes_zenodo_exploratory_result.json`. The GitHub files
are another copy of consumed data, so the prospective claim is invalidated.

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

No pass can be issued from this attempt. The frozen model remains reusable for
a genuinely untouched dataset. Pressure prediction, valve and line flow,
composite tanks, station control and accident consequences remain outside it.
