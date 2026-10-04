# MC Default measured-boundary vehicle-tank diagnostic

This replay uses the eight prospectively selected MC Default traces already
consumed by the frozen full-loop experiment. It passes the measured mass-flow,
inlet-gas-temperature and published source-pressure channels directly to the
Type-IV vehicle-tank submodel. The station controller, cascade dispatch,
compressor and dispenser hydraulics are removed from this replay.

The run is therefore a post-outcome **development diagnostic**, not a new
holdout and not a full-station validation. The frozen MC model multipliers are
used without case-specific fitting. The result isolates the remaining error:
pressure agreement becomes much better than the full loop (mean pressure RMSE
1.816 MPa with `source_pressure_3_mpa`), while temperature remains poor (mean
RMSE 25.884 °C) and final SOC error remains above the project screen (5.582
percentage points). The result indicates that the full-loop pressure failure is
dominated by station/source-boundary and controller/dispenser representation,
while the thermal boundary or tank thermal representation still needs an
independent MC-condition calibration.

This artifact does not change the frozen full-loop result and does not support
an IJHE full-loop or field-safety claim. It is retained to prevent future work
from treating the failed full-loop comparison as an undiagnosed single-model
failure.
