# Public component-data lead (2026-10-10)

The public `gadoseb/HSR-Rig-Project` repository contains one 24.85 MB example log with 168,476 rows, timestamped pressure, two temperatures, hydrogen flow, cumulative transferred hydrogen, strain channels, and 12 absorption/12 desorption phase pairs. The immutable source commit and raw-file SHA-256 are recorded in the adjacent JSON artifact.

This is **not** a hydrogen-refuelling-station dataset. It is a metal-hydride storage-reactor cycling rig. The repository has no explicit `LICENSE` file, so the raw rows are not copied into this project and are not treated as reusable validation data.

The lead is retained for three bounded purposes:

1. offline parser and phase-marker checks;
2. a physics-compatibility review for component-level pressure/thermal diagnostics; and
3. a future custodian-approved, de-identified data request.

It cannot close the station-to-vehicle full-loop gate and does not change runtime parameters or any IJHE readiness gate.
