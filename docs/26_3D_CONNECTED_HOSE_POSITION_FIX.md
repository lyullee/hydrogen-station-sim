# Connected fueling hose coordinate correction

Date: 2026-09-19

## User report

The charging hose between the passenger vehicle and dispenser was positioned incorrectly. The user requested correction after the issue had previously been disclosed.

## Fix

The connected hose previously received station-wide coordinates while being parented to the dispenser, adding its positional offset a second time. Its nozzle had the same coordinate mismatch.

The connection now starts in dispenser-local coordinates. A vehicle-local inlet anchor is transformed through the vehicle world matrix and then into dispenser-local coordinates. The hose endpoint and nozzle housing are constructed relative to that anchor, including the vehicle's vertical offset. The curve sags above the paving and approaches the inlet from the dispenser side.

The earlier parked nozzle is tagged at construction and hidden on the active connected dispenser, avoiding an unrelated floating nozzle near the car. An inlet socket and open fueling-door detail identify the connection on the vehicle.

## Scope

The known connected-hose coordinate defect is addressed by this change. Hose routing, dimensions and mechanical deformation remain illustrative; no new flow model, hose-length calculation, loads or safety compliance are implied. Existing physics/API/live-series contracts are unchanged and recurring enhancement remains paused.

No tests, execution, browser review or validation were performed.
