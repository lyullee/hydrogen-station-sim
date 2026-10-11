# Frontend regression evidence — 2026-10-12

- Command: `node --test tests/*.test.mjs`
- Result: **PASS — 16 passed, 0 failed**
- Source commit: `4e8d482c120a87900ec0295d7624a08739869890`

The run covers streamed UTF-8 reconstruction, separation of main and sensor LLM API namespaces, mapped equipment flow and overlapping incident bands, active and finished consequence ranges, radial versus directional geometry, regular-analysis OFF/ON behavior, manual-history isolation, and vehicle-specific fueling/shutdown signals.

This is a frontend/state-contract check only. It does not establish physical-model validity, field safety, or operator effectiveness.
