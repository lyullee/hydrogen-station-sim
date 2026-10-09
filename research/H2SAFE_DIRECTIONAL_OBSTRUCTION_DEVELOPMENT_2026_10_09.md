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

The machine-readable boundary and source hash are in
`h2safe_directional_obstruction_development_2026_10_09.json`.
