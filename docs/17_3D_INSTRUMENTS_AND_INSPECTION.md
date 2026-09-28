# 3D instruments and inspection interaction

Date: 2026-09-19

## Implemented

- Dispenser screen connected to nozzle flow, vehicle pressure, SOC and ESD from the existing result series.
- Cascade-bank screens display actual simulation pressure and selected dispatch/recharge status.
- PLC screen displays model time and normal/ESD status.
- Before simulation data arrives, screens show placeholders rather than invented readings.
- Second dispenser explicitly states that it is visual-only.
- High-resolution local canvas textures update only when simulation index/result changes, not on every rendered frame.
- Selected-equipment focus button moves the camera smoothly toward the equipment bounds.
- Asset identification plates, yellow service-access markings, decorative unloading connection cabinet and CCTV.

## Boundaries

Screen values are simulation results, not connected physical instruments. Decorative analog dial needles remain illustrative. Unloading cabinet and CCTV do not add process boundary conditions, security functionality or safety functions. Existing known vehicle-hose coordinate issue remains unchanged pending the user's decision.

No execution, tests, browser inspection or performance validation were performed.
