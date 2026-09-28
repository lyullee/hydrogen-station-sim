# FCEV layout clarification and fill-port correction

## Clarification

The visual vehicle uses the second-generation Toyota Mirai as its published packaging reference. That vehicle uses three 70 MPa hydrogen tanks. This is not a statement that every FCEV has three tanks.

An FCEV does not have an internal-combustion engine. Hydrogen and air react electrochemically in the front fuel-cell stack, while a rear electric motor drives the wheels. The lithium-ion traction battery stores regenerated energy and supplements fuel-cell output. Toyota describes the Mirai as a plug-less electric vehicle.

Primary references:

- Toyota Technical Review Vol. 66: https://global.toyota/pages/global_toyota/mobility/technology/toyota-technical-review/TTR_Vol66_E.pdf
- Toyota New Mirai Press Information 2020: https://global.toyota/pages/news/images/2020/12/09/1200/20201209_01_02_en.pdf
- Toyota USA 2026 Mirai overview: https://pressroom.toyota.com/the-2026-toyota-mirai-driving-the-future-with-style-range-and-innovation/

## Correction

- Moved the visual receptacle from the rear door area to the driver-side rear quarter panel.
- Moved the existing hose/nozzle target to the identical vehicle-local coordinate `[-1.95, 0.84, -0.965]`.
- Enlarged the under-hood identification to `FUEL CELL POWER UNIT` and explicitly marked `NO COMBUSTION ENGINE`.
- Added an articulated hood reference. The existing vehicle cutaway control now raises the hood while revealing the FC stack, PCU and air system.
- Retained the three-tank Mirai reference layout and the existing lumped vehicle tank solver.

## Limitations

- Fuel-door shape, hinge and exact production coordinates remain illustrative; the station hose endpoint and visual receptacle now share one coordinate.
- Hood motion is an inspection visualization, not production hinge kinematics.
- No new fuel-cell electrochemistry, traction motor or battery dynamic model was added.

## Validation

No browser execution, syntax check, test or post-edit visual inspection was performed for this correction.
