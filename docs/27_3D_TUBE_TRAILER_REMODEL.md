# Tube-trailer and tractor visual remodel

Date: 2026-09-19

## User request

Search for actual hydrogen transport vehicles and replace the overly blocky vehicle with a more realistic interpretation.

## Primary references

- FIBA tube trailers and skids: https://www.fibatech.com/products/tube-trailers-and-skids/
- FIBA modular trailers: https://www.fibatech.com/products/tube-trailers-and-skids/modular-tube-trailers/
- Volvo cab design discussion: https://www.volvotrucks.com/en-en/news-stories/stories/2024/feb/designing-a-truck-for-the-future.html
- Volvo FH exterior product information: https://www.volvotrucks.com/en-en/trucks/models/volvo-fh.html
- Calvera manufacturer photo/reference: https://www.calvera.es/calvera-hydrogen-develops-the-largest-ever-hydrogen-transport-tube-trailer-model-for-shell-hydrogen/

Image searches were used for visual context, including tube bundles mounted within structural frames and modern cab-over tractors. Technical interpretation relies on manufacturer sources. The model is deliberately unbranded and does not reproduce a specific manufacturer's CAD or claim the dimensions or payload of a particular product.

## Implemented

- New modular tube-trailer geometry builder in web/tube-trailer.js.
- Sculpted cab-over shell with changing width, rounded front corners and raked windshield.
- Side glazing, mirrors, door seams, handles, entry steps, roof details, wipers, front grille and lighting signature.
- Separate tractor/trailer chassis, articulation plate, service-line coils and side accessories.
- Three trailer axles, tractor axle arrangement, dual tires, metallic hubs, instanced wheel fasteners, fender and mudguard detail.
- Longitudinal gas-tube bundle, structural end supports, restraint bands, side diagonals and rear manifold/service area.
- Generic logistics labels, side rails, reflectors and marker lenses.
- Earlier transporter visuals are hidden while the supply equipment group remains in place, preserving selection and existing supply data binding.

## Limits

One scene unit is approximately one metre, but the compact model is fitted to the existing illustrative station layout. It is not an exact representation of a full-length commercial trailer. Tube count, fittings, cargo pressure, chassis load capacity, axle loads, air brake systems and road approval are not engineering specifications. The new geometry does not alter the existing supply boundary or create dynamic trailer blowdown, inventory or HyRAM inputs. Lighting is visual, not a vehicle electrical model.

Repeated primitive geometries are cached within the new builder, and hub screws use instancing. No measured rendering-speed claim is made. Recurring enhancement remains paused. No tests, execution, browser inspection or validation were performed.
