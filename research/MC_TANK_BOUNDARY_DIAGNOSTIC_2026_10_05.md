# MC Default measured-boundary vehicle-tank diagnostic

This replay uses the eight prospectively selected MC Default traces already
consumed by the frozen full-loop experiment. It passes measured mass flow and
the co-located vehicle-inlet pressure/temperature pair `Pinlet` and `Tinlet_G`
directly to the Type-IV tank submodel. The station controller, cascade dispatch,
compressor and dispenser hydraulics are removed from this replay.

The corrected replay gives mean pressure RMSE 4.376 MPa, temperature RMSE
9.052 °C and SOC RMSE 5.583 percentage points. Pressure and temperature are
within the project component screens on aggregate, while SOC remains above its
5 percentage-point screen. These aggregate values are not a joint case-pass
result.

Schema version 1 paired `Tinlet_G` with the upstream `875PT3` storage-source
pressure. That mixed two physical locations and produced an artificial
25.884 °C temperature RMSE. Schema version 2 supersedes that boundary choice.
The production simulator already transports hose enthalpy to the receptacle and
is unchanged by this diagnostic correction.

The run remains a post-outcome **development diagnostic**. It uses the tank
parameters frozen before the MC Default outcomes were opened and performs no
case-specific fitting. The result strengthens the diagnosis that the full-loop
failure is primarily in the station-side source boundary and
controller/dispatch approximation. The remaining SOC error and case-level
thermal spread still require new independent data before the tank model can be
revised or promoted.

This artifact does not change the frozen full-loop result and does not support
an IJHE full-loop or field-safety claim.
