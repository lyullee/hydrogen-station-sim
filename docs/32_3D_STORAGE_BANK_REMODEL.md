# Storage bank reference remodel

## Scope

Implemented stage 4 of the five-stage equipment realism plan. This is a visual replacement only. Simulation capacities, equations, pressure ratings, dispatch/recharge control, API and HyRAM inputs are unchanged.

## Primary reference

- FIBA Technologies, Hydrogen Distribution & Storage brochure, page 3: https://www.fibatech.com/wp-content/uploads/2021/09/Hydrogen-Pressure-Vessel-Brochure.pdf
- The Type II table lists a nominal 2.9 m vessel with 202 L water capacity. The brochure also discusses customized assemblies and cascade manifolds.
- The tabulated pressure rating is a manufacturer product specification, NOT a new setting or rating for the simulator banks.

## Implementation

- Added `web/storage-bank.js` and replaced all three original bank visual groups before equipment picking/menu construction.
- Six horizontal reference vessels per bank: composite-wrapped cylindrical center, exposed metallic shoulders/necks, individual isolation-valve appearance and vessel identifiers.
- Two-column, three-level rack with feet, anchor appearance, side bracing, crossmembers, saddle pads, retaining bands and fasteners.
- Vessel neck branches feed a front collector with separate fill/draw boundary fittings and a reserved relief reference port.
- Existing fill/draw coordinates remain `[.99,.40,2.03]` and `[.99,.65,2.03]` in bank-local coordinates, preserving the previously implemented station pipe endpoints.
- New visible pressure screens use the existing bank instrument renderer. New bank lights remain driven by the existing status-light logic.
- Hidden original visuals and their hidden screens remain allocated; replacing them does not remove the existing equipment groups or solver bank identifiers.

## Model boundary and limitations

- Nominal visual vessel length is about 2.9 m. Illustrative shell diameter is about 0.41 m; the central wrapping envelope is about 0.428 m. Public tabular capacity does not establish actual outer diameter, wall thickness or winding layup.
- These dimensions are NOT obtained by converting 202 L to an outer envelope. Six displayed vessels do not imply a 1,212 L bank in the solver.
- Three bank racks share one illustrative reference envelope; bank colors identify cascade groups, not certified pressure classes.
- Rack, anchors, saddle contact, retaining bands and manifold are appearance references, not seismic/wind calculations, pressure-boundary designs or manufacturer CAD reproductions.
- Static valve handles, relief fitting and composite texture are not additional dynamic states. Relief is not yet connected to a vent header at this stage.
- No certification, vessel structural integrity or safety-distance compliance is claimed.

## Progress

1. Ports and physical pipe routes: implemented.
2. Refrigeration, HTF circulation and high-pressure heat exchanger: implemented.
3. Compressor skid and coherent service enclosure: implemented.
4. Storage vessel proportions, supports and manifolds: implemented.
5. Vent header, base/supports and discharge detail: remaining.

## Validation

No tests, syntax checks, browser runs or post-edit inspection were performed. Implementation completion is distinct from runtime validation.
