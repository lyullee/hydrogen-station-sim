# Reference-based compressor skid and service enclosure

Date: 2026-09-19

## Primary references

- PDC hydrogen-refueling compressor applications and instrumented skid examples: https://www.pdcmachines.com/hydrogen-compressors-for-hydrogen-refueling-stations/
- PDC hydrogen compressor flyer: https://www.pdcmachines.com/wp-content/uploads/2022/08/H2-Compressors-for-Refueling-Stations-Flyer-1.pdf

The application page was fetched for this stage. It documents diaphragm compressors in instrumented and containerized station packages. An image search restricted to the manufacturer's domain returned no results; no externally retrieved photo or proprietary CAD is embedded. The modeled assembly is a functional visual interpretation, not a reconstruction of a specific PDC machine.

## Implemented

- New web/compressor-package.js geometry module.
- Supported skid rails, crossmembers, feet and plinth anchors.
- Finned electric motor, coupling guard and common drive/hydraulic-case visual form.
- Three differently sized circular diaphragm-reference heads with layered flange faces and instanced bolts.
- Cooling assemblies, gas-stage connections, instrument manifold and decorative pressure dials marked as visual.
- Hydrogen ports retain the local anchors used by station physical piping and animated overlays.
- Permanent enclosure framework with removable roof, side skins and front service doors.
- Exterior handles, louvres and identification panels are children of the removable skins so they disappear together in service view.
- Existing recharge/ESD indicator state is bound to the replacement compressor package.

## Scope

The visual three-stage arrangement follows the current simulator's stage abstraction, not a claim that a particular PDC product has exactly three heads or this layout. Diaphragm displacement, hydraulics, crankshaft motion, instrument dynamics, coolant services and component dimensions are illustrative. The process model retains its existing efficiency, motor-power and recharge equations; no new process nodes or HyRAM inputs are created. Decorative dial needles do not display measured or calculated stage pressure.

Primitive geometries are cached inside the builder and head screws use instancing. No measured performance or safety-compliance claim is made.

## Five-item implementation status

1. Equipment ports and barrier-bypass route: implemented; unvalidated.
2. Chiller, circulation and high-pressure HEX separation: implemented; unvalidated.
3. Reference-based compressor skid and service enclosure: implemented; unvalidated.
4. Reference-based storage vessel proportions and supports: remaining.
5. Vent header, support/base and reference-based outlet: remaining.

No tests, execution, browser inspection, syntax check or validation were performed.
