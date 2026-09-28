# 3D station operations view - 2026-09-19

## Implemented visualization

Added a local Three.js 0.160.0 scene above the existing process diagram, preserving
the Python simulation, API, live streaming, and replay interfaces. The procedural
model includes a canopy, two dispenser islands, FCEV, tube trailer, three cascade
racks, compressor enclosure, precooler/chiller, safety PLC, vent stack, barrier wall,
fence, bollards, marked lanes, lights, and landscaping.

Operator interactions include orbit/zoom/pan, four camera presets, equipment picking
and information cards, process-line visibility, transparent canopy, and night lights.
Live or replayed process data drives vehicle pressure/temperature/SOC, flow, bank
pressure, dispatch/recharge selection, status LEDs, ESD colors, and flow particles.

## Boundaries

This is a conceptual operational visualization, not a surveyed or approved P&ID,
CAD, separation-distance, vent, structural, or code-compliance model. The second
dispenser, trailer body, lighting, and landscaping are visual context. The supply
remains a P/T boundary in the process model. Cooler -40 C text is a setpoint, not a
newly added measured variable. Vent-stack detail dynamics are not implied.

Three.js and OrbitControls are vendored with the MIT license under web/vendor/three.
No CDN is required at runtime. Pixel ratio and render cadence are limited; rendering
pauses when off-screen or when the browser is hidden. No validation was run as part
of this visual implementation task.

## Primary references

- H2Tools gaseous station hardware overview:
  https://h2tools.org/bestpractices/gaseous-gh2-and-liquid-hydrogen-lh2-fueling-stations
- NREL hydrogen infrastructure research facility:
  https://www.nrel.gov/hydrogen/hitrf-animation?print=
- H2FIRST reference station design:
  https://h2tools.org/sites/default/files/fcto_h2first_reference_station_design_report_april2015_0.pdf
- Three.js installation and OrbitControls:
  https://threejs.org/manual/pages/installation.html
  https://threejs.org/docs/pages/OrbitControls.html
