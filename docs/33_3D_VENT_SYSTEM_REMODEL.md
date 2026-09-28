# GH2 vent reference system

## Primary references

- EIGA Doc 211/24, Hydrogen Vent Systems for Customer Applications: https://www.eiga.eu/uploads/documents/DOC211.pdf
- H2Tools, Venting for Gaseous and Liquid Hydrogen webinar Q&A: https://www.h2tools.org/sites/default/files/2024-07/Venting%20for%20Gaseous%20and%20Liquid%20Hydrogen%20Webinar%20Q%26As.pdf

## Reference principles

EIGA discusses simultaneous release sizing and backpressure, structural loads and thrust resilience, upward outlets, water drainage, debris protection and electrical continuity. Outlet location requires exposure assessment. H2Tools discusses sparse stainless bars as an alternative to mesh, with flow restrictions requiring assessment. These references inform appearance; they do not validate this station layout.

## Implementation

- Added `web/vent-package.js`, replacing the old stack appearance while preserving its equipment identifier and group position.
- Existing storage reference relief ports feed individual branches routed beside the racks to a rear header at world z = -9.85 m. The header turns toward the stack inlet.
- Explicit tubing, header supports, foundation, anchor appearance, base plate, bolted flange appearance, support mast and clamps.
- Approximately 8 m visual outlet elevation, retained as a scene-scale choice, not a calculated requirement.
- Open-ended upward outlet with sparse reference debris bars rather than a solid cap or flame arrestor.
- Low-point drain fitting and bonding-wire appearance. No actual grounding network or drainage functionality is simulated.
- Visible labels explicitly distinguish the header and stack from dynamic flow and safety calculations.
- No flames, visible hydrogen clouds or animated release particles imply an actual vent event.

## Boundaries

- GH2 illustration only; not an LH2 vent design.
- Shared header connection is illustrative, not proof that devices can be combined safely. Simultaneous releases, backpressure, device ratings and compatibility have not been evaluated.
- Header and branch diameters, pipe wall, flange design, supports and anchors are illustrative.
- Debris bars and open outlet do not establish weather protection. Rain ingress, drain performance, freezing and blockage require engineering review.
- No relief-valve dynamics, header inventory, compressible vent network or structural calculations were added.
- API, solver and HyRAM inputs remain unchanged. Existing vent-card live reading remains unconnected to a calculated vent flow.
- Not a safety-distance, pressure-rating, electrical-continuity or regulatory compliance determination.

## Five-stage implementation status

1. Equipment ports and routed physical piping: implemented; docs/29.
2. Refrigeration, circulation/buffer and high-pressure heat exchanger: implemented; docs/30.
3. Compressor skid, heads, intermediate cooling and service enclosure: implemented; docs/31.
4. Reference storage vessels, rack and manifold: implemented; docs/32.
5. Vent header, foundation/supports and discharge detail: implemented; this record.

The agreed five-stage 3D implementation scope is complete. This does not mean all simulator physics, certifications or execution validation are complete. Stop the recurring improvement task rather than indefinitely adding scenery.

## Validation

No tests, syntax checks, browser execution or post-edit inspection were performed. Runtime behavior and rendering remain unvalidated.
