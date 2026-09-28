# Equipment ports and coherent physical piping

Date: 2026-09-19

## Implementation

- Added web/station-piping.js for explicit equipment-local connection anchors, shared route definitions and physical piping construction.
- Supply connection is anchored at the detailed trailer's rear manifold region.
- Compressor inlet/outlet, storage fill/draw connections, cooler inlet/outlet and dispenser connections use their equipment group transforms.
- Fueling route bypasses the barrier at x=15.2, beyond its x=14.5 end, instead of crossing through the solid wall.
- Physical steel tubing and animated colored process overlays use the same route definitions.
- Line segments and rounded elbow transitions replace broad spline wandering on the process routes.
- Added port flanges and route supports.
- The standby-dispenser branch is explicitly visual-only and receives no animated process flow.
- Existing supply, dispatch, recharge, fueling and ESD animation identifiers are preserved.

## Scope and references

The routing is a conceptual interpretation, not a certified pressure-piping layout. Pipe diameter, class, fittings, support loads, access widths, fire-wall clearances and transport connection procedures require engineering design. The bypass is a geometric route choice, not a safety-compliance determination. No process nodes, pressure-drop equations, supply boundary conditions or HyRAM inputs have changed.

Station topology reference: https://www.pdcmachines.com/wp-content/uploads/2023/02/PDC_Brochure_V21_USA_SM.pdf

Transport equipment reference: https://www.fibatech.com/products/tube-trailers-and-skids/

## Five-item implementation status

1. Equipment ports and barrier-bypass route: implemented; runtime/visual validation not performed.
2. Separate chiller, circulation and high-pressure heat exchanger: remaining.
3. Reference-based compressor skid and service enclosure: remaining.
4. Reference-based storage vessel proportions and supports: remaining.
5. Vent header, support/base and reference-based outlet: remaining.

No tests, execution, browser inspection or validation were performed. The existing scheduled task remains responsible for subsequent stages and final automatic stopping.
