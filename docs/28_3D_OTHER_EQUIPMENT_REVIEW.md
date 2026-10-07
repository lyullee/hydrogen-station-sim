# Review of remaining station equipment visuals

Date: 2026-09-19

## Scope

User requested a review of the other equipment after the transporter remodel. This review compares the known implemented geometry with primary manufacturer and hydrogen-system references. It is not a browser inspection, code re-read, execution test, engineering certification or review of the process equations. No implementation files were modified.

Relevant implementation: `web/station3d.js`

## Findings in priority order

### 1. Process piping passes through the barrier without modeled penetrations

The barrier is centered at z=-1.7, reaches roughly y=1.85 and spans x=-8.5 to x=14.5. The known fueling routes cross this location near x=12 or x=12.4 at y=0.45 or y=0.67. No penetration sleeve, opening or alternative routing is represented. This makes the physical scene internally inconsistent, even though the colored lines are also a process-flow visualization.

Recommended next change: define visible equipment ports and separate the physical pipe route from the colored flow overlay. Provide explicit visual penetrations or a route around the barrier. Do not imply an approved fire-barrier penetration detail without engineering documentation.

### 2. Chiller and hydrogen precool heat exchanger are visually conflated

Current equipment combines a generic fan-topped cabinet, refrigeration accessories and the precooler label. It does not clearly identify the high-pressure hydrogen heat exchanger or distinguish the heat-transfer-fluid supply and return from the hydrogen route.

Mydax describes chiller systems, reservoir/pump modules and stainless microchannel hydrogen precooler heat exchangers. PDC's station schematic separately identifies Chiller and Pre-Cool HEX.

Recommended next change: visually distinguish the refrigeration cabinet, circulation/buffer module and insulated high-pressure heat exchanger. Select an air-cooled or water-cooled reference consistently; not every chiller needs roof fans. Keep the current physics unchanged unless the user requests process-model changes.

Sources:

- https://mydax.com/hydrogen-refueling/
- https://www.pdcmachines.com/wp-content/uploads/2023/02/PDC_Brochure_V21_USA_SM.pdf
- https://mydax.com/water-cooled/

### 3. Compressor internals are generic, not tied to a selected compressor technology

The green enclosure and illustrative three-head arrangement communicate compression, but do not correspond to an identified compressor manufacturer's machine geometry. The service view needs a coherent support skid, drive mechanism, compressor heads, cooling services and instrumentation rather than isolated generic cylinders. Hiding the outer shell also leaves exterior trim visible in the current visual approach.

PDC provides primary examples of diaphragm compressors in open instrumented skids and containerized hydrogen stations. These are suitable references, but do not establish that every hydrogen compressor must be diaphragm-based or have three stages.

Recommended next change: choose a diaphragm-skid visual reference, model its distinctive head/drive arrangement and service piping, and provide purposeful removable panels. Identify it as an illustrative visual reference. Do not claim that the existing thermodynamic compression model resolves diaphragm mechanics.

Sources:

- https://www.pdcmachines.com/hydrogen-compressors-for-hydrogen-refueling-stations/
- https://www.pdcmachines.com/wp-content/uploads/2022/08/H2-Compressors-for-Refueling-Stations-Flyer-1.pdf

### 4. Storage vessels have unreferenced diameter, finish and volume

The three banks currently use identical six-vessel arrangements with shiny metal finish. Their pressure identities are correctly distinct in the visual data, but vessel construction and dimensions are not derived from a selected product.

Treating one scene unit as one metre, the implemented radius 0.32 and cylindrical length 3.2 imply approximately pi*0.32^2*3.2 + 4*pi*0.32^3/3 = 1.17 cubic metres per capsule. This is a geometric estimate, not a comparison with the unread process configuration. Six such shapes represent about 7 cubic metres visually. A consistent visual-to-process volume comparison is therefore needed before suggesting dimensional accuracy.

FIBA describes several vessel constructions, including steel and composite storage. Its public brochure lists manufacturer-specific capacities and lengths rather than a universal rack dimension.

Recommended next change: choose vessel construction and a capacity/diameter/length family, calculate a consistent illustrative envelope from the chosen reference, and improve end bulkheads, neck valves, restraint supports and header connections. Do not silently replace the simulation's bank capacities with catalog values.

Sources:

- https://www.fibatech.com/hydrogen-pressure-vessels-2/
- https://www.fibatech.com/wp-content/uploads/2021/09/Hydrogen-Pressure-Vessel-Brochure.pdf

### 5. Vent stack is not visually connected to a relief/vent system

The present tall pipe, support rods and ladder identify a stack, but do not show its source header, drainage/access provisions or a selected discharge arrangement. Its existing information card appropriately states that detailed vent flow is unconnected.

Recommended next change: add an explicitly illustrative vent header, support/base detail and a reference-based top arrangement. Stack diameter/height, weather protection, discharge direction and vent scenarios must not be inferred from appearance alone. Detailed design requires flow, temperature, backpressure, thrust and dispersion/radiation assessment; no safe height or compliance claim is made here.

Source:

- https://www.h2tools.org/sites/default/files/2024-07/Venting%20for%20Gaseous%20and%20Liquid%20Hydrogen%20Webinar%20Q%26As.pdf

## Lower-priority remaining items

- Active dispenser remains a generic model while the standby dispenser has a referenced compact envelope. A reference-based active dispenser panel/nozzle/support design would improve consistency, but different physical dispenser models are not inherently wrong.
- PLC cabinet and detector fixtures need selected hardware references for precise housings and mounts. Their visual presence does not establish certification, sensor coverage or independence of the actual hardware.
- Small fittings should be simplified when distant, rather than indefinitely increasing detail or draw calls.

Dispenser reference: https://tatsuno-corporation.com/en/products/h2dispenser/hydrogen-nx/

## Suggested implementation sequence

1. Equipment ports and physical pipe routes.
2. Chiller/precool heat-exchanger distinction.
3. Compressor skid and enclosure redesign.
4. Referenced storage vessels and rack structure.
5. Vent system and active dispenser refinement.

Existing API, simulation state, HyRAM integration and recurring-automation pause are unchanged. No tests or runtime validation were performed.
