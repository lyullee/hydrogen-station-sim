# HIAD-to-digital-twin canonical replay coverage

This audit checks whether each public HIAD HRS metadata family can enter the
actual digital-twin runtime. It uses declared canonical fault fixtures because
the incident inventory has no synchronized process boundary traces.

- Public HIAD HRS cases: **34**
- Direct physical replay coverage: **29** cases
- Bounded proxy/partial replay: **4** cases
- Response-only, no physical model: **1** case
- Unmapped: **0** cases
- Executable canonical recipes passed: **9/9**

## Canonical runtime traces

| Family | Representation | Result | Runtime evidence |
| --- | --- | --- | --- |
| `gas_release` | `direct_physical_replay` | `passed` | alarms GD-0801, GD-2201; releases 1 |
| `hydrogen_fire` | `direct_physical_replay` | `passed` | alarms FD-0801, GD-0801, GD-2201; releases 1; flame FD-0801 |
| `hose_connection` | `direct_physical_replay` | `passed` | alarms GD-1301, GD-2301; releases 1 |
| `overpressure` | `direct_physical_replay` | `passed` | alarms PT-0801, TT-0801 |
| `precooling_fault` | `direct_physical_replay` | `passed` | trips precooling-temperature-high |
| `fueling_fault` | `direct_physical_replay` | `passed` | alarms FT-1101, FT-1301, FT-1501, FT-1701, PT-1101, PT-1501 |
| `compressor_thermal` | `proxy_partial_replay` | `passed` | alarms FD-0601; flame FD-0601 |
| `external_fire` | `direct_physical_replay` | `passed` | alarms FD-0801; flame FD-0801 |
| `isolation_failure` | `proxy_partial_replay` | `passed` | alarms FT-1501, FT-1701, PT-1102, PT-1401, PT-1501, TT-1401 |
| `structural_damage` | `response_only_no_physical_model` | `not_run_no_physical_model` | staged response plan only |

## Interpretation boundary

- HIAD metadata selects a response family; incident narratives do not set pressure, temperature, opening size, enclosure geometry or timing in the canonical recipes.
- A passed trace shows that the declared family can traverse process physics, virtual detection, HAZOP/safety logic, native consequence calculation where applicable, and a registered response-plan handoff.
- It does not reconstruct any HIAD accident, validate accident frequencies or safe distances, establish operator benefit, or show that an action is correct or effective.
- Compressor thermal events remain a partial proxy because the compressor has no separate dynamic inventory, and structural damage remains response-only because structural mechanics are outside the model.

The JSON artifact contains source hashes, exact canonical fault inputs,
required checks, observed sensors, safety trips, releases and consequence
statuses for reproducible review.
