# H2SAFE directional and obstruction-aware development candidate

The existing coordinate-only detector ranker treats every release as a buoyant
vertical plume. H2SAFE publishes a horizontal release case and HVAC metadata,
so the next candidate now accepts three explicit inputs in one coordinate frame:

- the release-jet direction;
- ventilation velocity vectors; and
- equipment or wall obstruction geometry.

`directional_obstruction_geometry_score` in
`src/h2station/spatial_detector.py` combines these with the frozen
orientation-class rank. Its gains are fixed physical priors and were not fitted
to H2SAFE outcomes. A line-of-sight obstruction multiplies the score by `0.6`
per intersecting box; this is a development visibility heuristic, not a CFD
transmission coefficient.

The H2SAFE HVAC document contains speeds and areas, but Lab-2 does not publish
duct coordinates or velocity vectors in the sensor frame. Treating a scalar
speed as a direction would manufacture validation evidence, so no numerical
candidate score is reported. The candidate is retained for a new pre-access
holdout and is prohibited from runtime detector routing.

The parser and input-readiness boundary are frozen in
`h2safe_hvac_input_readiness_2026_10_12.json` (human-readable summary:
`H2SAFE_HVAC_INPUT_READINESS_2026_10_12.md`). It records four missing inputs:
the release direction vector, same-frame HVAC vectors, independently checked
mesh registration, and the release-to-trace time crosswalk. The artifact is
metadata-only and does not redistribute trace rows.

The public OEDI package does contain ASCII STL/STEP geometry. The follow-up
containment diagnostic
`h2safe_geometry_sensor_containment_2026_10_12.json` confirms that all 61
published sensor coordinates and both documented release coordinates fall inside
their matching mesh bounding boxes. This is useful evidence for a candidate
obstruction frame, but bounding-box containment is not an independent mesh
registration; runtime use and pre-access validation remain closed.

The machine-readable boundary and source hash are in
`h2safe_directional_obstruction_development_2026_10_09.json`.
