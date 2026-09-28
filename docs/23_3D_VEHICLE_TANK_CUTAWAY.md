# Vehicle underfloor tank visualization

Date: 2026-09-19

## Primary reference

Toyota, The New Toyota Mirai:

https://newsroom.toyota.eu/the-new-toyota-mirai/

Toyota describes a long longitudinal center tank and two shorter transverse tanks beneath the rear seating/luggage areas. This packaging arrangement informed the visual example. The passenger vehicle is not a Toyota CAD reproduction and no published capacity has been substituted into the simulator.

## Implemented

- New vehicle-tank cutaway toggle makes the main body translucent and reveals an underfloor tank group.
- Three illustrative Type IV vessel shapes: one longitudinal and two rear transverse.
- Locally generated composite surface pattern, mounting straps, supports, valve fittings and manifold tubing.
- Existing vehicle card clarifies that these objects illustrate the aggregate tank model rather than independently calculated tanks.

## Limits

Tank dimensions, orientation details, valve mechanisms, mounting loads and crash clearances are illustrative. Composite texture is an artistic surface, not laminate modeling. Physics still uses its existing vehicle model and thermal layers; no new process nodes, inventories, fuel-cell model or HyRAM inputs are created. The known active vehicle-hose coordinate issue remains awaiting user approval.

No tests, execution, browser inspection or validation were performed.
