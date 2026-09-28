# Station site context and utility detail

Date: 2026-09-19

This visual-only stage expands the station surroundings, preserving the physics and API.

- Public road with lane markings, sidewalk joints, pedestrian crossing and tactile tiles.
- Industrial background building, roller doors and glazing.
- Side fences, utility-yard access gate and restricted-entry signs.
- Static stainless process tubing, supports, flanges and valves, independently of the colored operational overlay.
- Illustrative earthing conductors and cable tray.
- Emergency response point and attendant figure for scale.
- Fence wires and tactile dots use instancing to avoid one draw call per repeated detail.

## Boundaries

These are illustrative visual objects. The attendant is not a HyRAM occupant input, road geometry is not a traffic simulation, and static tubing does not introduce new process nodes. Pipe class, approved routing, road dimensions, equipment setbacks and emergency facilities require site engineering documentation.

No execution, browser review or performance validation was performed in this stage.

## Known issue awaiting user decision

The vehicle-connected hose introduced in the previous stage mixes scene coordinates with dispenser-local coordinates. Its position can be offset. User approval to correct this was requested before this stage; the issue has not been silently corrected.

Reference: https://h2tools.org/bestpractices/gaseous-gh2-and-liquid-hydrogen-lh2-fueling-stations
