# Vehicle-tank boundary repair note (2026-10-11)

This note records a non-default model capability added while triaging the
negative MC Default vehicle-tank replay. It does not revise the frozen public
holdout or promote a post-outcome result.

## Change

`CompositeVehicleTank.initial_state_from_mass_temperature()` now accepts a
synchronized observed hydrogen mass and gas temperature. It derives the EOS
pressure from mass, effective volume and temperature instead of silently
forcing an inconsistent pressure/volume pair. The existing pressure/temperature
initializer remains the production default, so current station behavior and
the frozen validation artifact are unchanged.

## Boundary test

The path was exercised against the eight already-consumed MC Default traces by
using `capacity × initial SOC` as a **proxy** for initial mass. That proxy is
not an independent mass measurement and is therefore diagnostic only.

| Initialization | Joint screen | Mean pressure RMSE | Mean temperature RMSE | Mean SOC RMSE |
|---|---:|---:|---:|---:|
| Existing pressure/temperature EOS boundary | 0/8 | 4.376 MPa | 9.052 °C | 5.584 %-point |
| SOC-derived mass/temperature boundary | 0/8 | 4.780 MPa | 9.119 °C | 6.046 %-point |

The result shows that the frozen MC miss is not repaired by changing only the
initial mass boundary. The proxy also creates an initial pressure residual, so
it must not be used as a validation input.

## Claim boundary and next required evidence

The new path is intended for a future independently frozen event containing an
attested receiving-vessel mass (or equivalent calibrated inventory), pressure,
temperature and geometry. A future protocol must also declare whether the
reported tank-temperature channel is gas, liner, shell, or a measurement
operator over multiple sensors. Until those fields are available, the MC and
NREL results remain component diagnostics and the full-loop gate remains open.
