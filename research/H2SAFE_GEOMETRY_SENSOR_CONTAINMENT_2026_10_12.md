# H2SAFE geometry and sensor containment diagnostic

- Status: **CONTAINMENT_CONFIRMED_REGISTRATION_UNPROVEN**
- Source DOI: `https://doi.org/10.7799/17118570`
- Sensor containment: `61/61` (`1.000`)
- Release points inside mesh bounds: `{'lab_1': True, 'lab_2': True}`
- Runtime application: **false**

## Interpretation

The public geometry and sensor/release coordinates are mutually contained at bounding-box level. This does not prove mesh-to-sensor registration, vent vectors, release azimuth, obstruction semantics, or time alignment.

## Lab-level checks

- `lab_1`: sensors `24/24` inside the STL bounding box; release point inside bounds `True`.
- `lab_2`: sensors `37/37` inside the STL bounding box; release point inside bounds `True`.

Next action: Use the published meshes as a candidate obstruction frame only after an independently documented registration and a release-to-trace clock crosswalk are frozen.

> This is a geometry-containment diagnostic only. It is not a CFD result, detector-placement validation, hydrogen-model calibration, consequence-distance estimate, or runtime safety claim.
