# Frontend regression test run — 2026-10-11

`node --test tests/*.test.mjs` completed with **16 passed, 0 failed**.

The run covers stream reconstruction, separation of main and sensor assistant
APIs, equipment-to-flow mapping, overlapping incident bands, active/recent risk
range state, radial versus directional geometry, regular-analysis ON/OFF and
manual-history isolation, and vehicle-specific fueling routes.

This is a frontend/state-contract check only. It does not validate the physical
model, field safety distance or operator effectiveness.
