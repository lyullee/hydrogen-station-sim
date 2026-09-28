# Chiller, circulation and hydrogen heat exchanger decomposition

Date: 2026-09-19

## Primary sources

- Mydax hydrogen refueling: https://mydax.com/hydrogen-refueling/
- Mydax water-cooled equipment concept: https://mydax.com/water-cooled/
- PDC station schematic with separate Chiller and Pre-Cool HEX: https://www.pdcmachines.com/wp-content/uploads/2023/02/PDC_Brochure_V21_USA_SM.pdf

The Mydax sources were fetched for this stage. Their reservoir/pump, heat-transfer-fluid and microchannel hydrogen heat-exchanger descriptions informed the decomposition. The water-cooled interpretation does not copy a named product or assert that generic water-cooled catalog models meet the hydrogen station's temperature/capacity requirements.

## Implemented

- New web/cooling-package.js module.
- Separate water-cooled refrigeration cabinet, insulated HTF reservoir/pump skid and high-pressure hydrogen heat-exchanger assembly.
- Chiller service panels reveal illustrative refrigeration accessories and condenser plates.
- Insulating HEX jacket can be hidden with the existing equipment-interior control.
- Insulated HTF supply/return paths have distinct blue identification collars and visual-loop labels.
- Facility-water connections terminate at a visual boundary label; no tower or building cooling system is implied.
- Hydrogen ports share exported local anchors with station routing, preserving flow-overlay alignment.
- Older fan-topped cooler visuals are hidden; their fan animation entries are removed and cover controls reference the new panels.
- Existing fueling/ESD status indication is connected to a new package indicator.

## Scope

This is a visual decomposition, not a new refrigeration or circulation model. Refrigerant selection, cooling-water conditions, HTF flow rate, pump sizing, fluid compatibility, exchanger channel geometry, pressure rating and certified temperature performance require detailed engineering. No remote assets or new Python dependencies are introduced. Physics, API and HyRAM remain unchanged; -40 C is labeled as a model setpoint, not a measured HEX outlet value.

## Five-item implementation status

1. Equipment ports and barrier-bypass route: implemented; unvalidated.
2. Chiller, circulation and high-pressure HEX separation: implemented; unvalidated.
3. Reference-based compressor skid and service enclosure: remaining.
4. Reference-based storage vessel proportions and supports: remaining.
5. Vent header, support/base and reference-based outlet: remaining.

No tests, execution, browser inspection, syntax check or validation were performed.
