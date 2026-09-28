# 3D initialization error fix

Date: 2026-09-19

## User report

The user reported that the 3D section appeared but its model area was blank.

## Known code cause addressed

The decorative gauge helper created meshes without returning an object. Trailer construction subsequently accessed the returned object's rotation. The resulting undefined access can stop buildStation before event handlers and the render loop are registered.

The helper now constructs a positioned gauge group, puts its housing and dial face in local coordinates, and returns the group. The trailer rotation can consequently apply to the complete gauge assembly.

## Error visibility

Station construction is now wrapped in an initialization error handler. An initialization exception displays its message in the 3D area rather than leaving an unexplained empty panel. The existing non-3D dashboard and calculation model are unchanged.

## Remaining scope

The previously disclosed vehicle-hose coordinate issue is not changed by this rendering fix. Recurring visual enhancement remains paused as requested. No execution, tests, browser inspection or verification were performed; the user should reload the browser to observe the result.
