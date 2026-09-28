# Surface finish and form refinement

Date: 2026-09-19

## Visual improvements

- Rounded sheet-metal housings for the compressor, chiller, PLC and dispensers.
- Curved passenger-vehicle profile using quadratic curves instead of straight silhouette segments.
- Increased radial resolution for shared cylinder/capsule construction helpers.
- Shared, locally generated brushed-metal roughness texture for steel and fittings.
- Soft local contact-shadow textures beneath the vehicle and main equipment.

## Scope and resource considerations

Existing simulation values, API contracts and equipment identifiers are unchanged. No remote texture assets were introduced. Surface textures and contact-shadow material are shared; rounded housing geometries replace their previous box geometries and dispose the replaced geometry. Cylinder resolution is higher and may increase geometry workload; no measured performance claim is made.

Contact shadows are artistic ambient shading, not a physical illumination solver. Housing shapes do not claim manufacturer-CAD accuracy. The previously disclosed vehicle-hose coordinate issue is still awaiting user approval and is not modified in this stage.

No tests, execution, browser review or verification were performed.
