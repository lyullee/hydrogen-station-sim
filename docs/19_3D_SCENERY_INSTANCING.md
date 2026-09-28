# Repeated scenery rendering consolidation

Date: 2026-09-19

## Change

Repeated immutable scenery meshes are grouped by geometry parameters, material identity and shadow flags. Groups with six or more matching box, cylinder or torus objects are replaced by one InstancedMesh, preserving the original local transforms. Instancing is applied only to an explicit set of scenery parents.

Targets include eligible road markings, pavement details, utility supports and decorative hardware. Transparent surfaces, existing instanced objects, invisible objects, equipment-selection groups and animation objects are excluded. Registered equipment meshes are not replaced, so equipment selection and live state remain on their existing objects. Instance bounds are computed as part of construction for culling.

Fastener geometries are additionally cached by size and shared across equipment bolt groups.

## Measurement boundary

This is a structural reduction in submissions for eligible repeated objects, not a measured FPS improvement. Scene construction records the number of consolidated objects and batches in the panel's data attributes; no benchmark, browser execution or verification has been performed.

No additional dependencies or external assets are introduced. Physics and API are unchanged. The previously disclosed vehicle-hose coordinate issue remains awaiting user approval.
