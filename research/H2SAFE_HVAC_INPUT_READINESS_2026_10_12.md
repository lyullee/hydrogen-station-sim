# H2SAFE HVAC spatial-input readiness

- Status: **NOT_READY_FOR_PREACCESS_SPATIAL_VALIDATION**
- Source DOI: `https://doi.org/10.7799/17118570`
- Metadata SHA-256: `e99119f5f9aadac6e0bd8269b3fc7989a6026bc0a4c68221ea2a54b1eeee58bb`
- Runtime application: **false**

## Parsed public metadata

- Release tests: Lab 1 `1`, Lab 2 `4`
- Lab 1 ventilation records: `10`
- Lab 2 duct records: `8`
- Lab 2 recirculation fans: `2`

## Required inputs

- `release_direction_vector`: **missing** — The metadata declares horizontal/vertical orientation but no azimuth or common-frame 3-D jet vector.
- `ventilation_velocity_vectors`: **missing** — Speeds and areas are published, but the vents/ducts lack origins and common-frame 3-D vectors.
- `obstruction_geometry`: **missing** — STEP/STL meshes are present, but no independently checked registration from mesh coordinates to sensor coordinates is declared.
- `release_to_trace_time_crosswalk`: **missing** — Release wall-clock/duration metadata is not aligned to the CSV-relative logger time axis.

## Gate interpretation

The metadata is sufficient to write a transparent candidate and unit-test parser behavior. It is not sufficient for a pre-access spatial validation because the release/HVAC vectors, registered obstruction geometry and release-time crosswalk are not jointly declared in one frame.

Next action: Obtain a rights-cleared cohort with release vectors, HVAC vectors, registered obstruction geometry, signal units and a release-to-trace time crosswalk, then freeze candidate before outcome access.

> This audit parses public HVAC metadata and makes missing common-frame inputs explicit. It is not a hydrogen concentration model, CFD result, detector placement validation, alarm/ESD validation, consequence-distance estimate or HRS full-loop validation.
