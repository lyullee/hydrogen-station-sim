# KHK public accidents to digital-twin canonical replay coverage

This independent integration audit traces public KHK accident metadata
through declared digital-twin fault recipes. It is not accident reconstruction
or evidence that the simulated response is effective.

- Public reports / incident codes: **23 / 26**
- In-scope reports / incident codes traced: **22 / 25**
- Direct canonical family traces: **12** reports
- Bounded proxy/partial traces: **10** reports
- Explicitly out of scope: **1** report
- Family recipes passed: **8/8**

## Report-level trace

| Incident code(s) | Equipment class | Representation | Runtime result |
| --- | --- | --- | --- |
| 2024-349 | `hydrogen_generation` | `out_of_scope_non_hydrogen_chemical` | excluded: non-H2 chemical |
| 2023-434 | `dehumidifier_ignition` | `proxy_partial_replay` | passed |
| 2023-330 | `explosion` | `proxy_partial_replay` | passed |
| 2023-188 | `filling_equipment_explosion` | `proxy_partial_replay` | passed |
| 2023-100 | `vehicle_fire` | `proxy_partial_replay` | passed |
| 2022-608 | `storage_fitting_leak` | `direct_canonical_family_replay` | passed |
| 2022-030 | `fitting_leak` | `direct_canonical_family_replay` | passed |
| 2021-552 | `leak_static_ignition` | `proxy_partial_replay` | passed |
| 2020-144 | `hydrogen_leak` | `direct_canonical_family_replay` | passed |
| 2019-378 | `filling_hose_damage` | `direct_canonical_family_replay` | passed |
| 2018-660, 2018-661 | `compressor_leak` | `proxy_partial_replay` | passed |
| 2018-705 | `hose_leak_detector_alarm` | `direct_canonical_family_replay` | passed |
| 2017-101 | `filling_hose_rupture` | `direct_canonical_family_replay` | passed |
| 2017-037, 2017-094, 2017-119 | `dispenser_leak` | `direct_canonical_family_replay` | passed |
| 2016-1066 | `isolation_valve_leak` | `proxy_partial_replay` | passed |
| 2016-186 | `breakaway_coupling_leak` | `direct_canonical_family_replay` | passed |
| 2016-082 | `station_hydrogen_leak` | `direct_canonical_family_replay` | passed |
| 2015-363 | `mobile_breakaway_leak` | `direct_canonical_family_replay` | passed |
| 2015-333 | `dispenser_isolation_valve_leak` | `proxy_partial_replay` | passed |
| 2015-052 | `dispenser_fitting_leak` | `direct_canonical_family_replay` | passed |
| 2014-349 | `accumulator_fire` | `proxy_partial_replay` | passed |
| 2014-182 | `filling_hose_leak` | `direct_canonical_family_replay` | passed |
| 2005-415 | `station_explosion` | `proxy_partial_replay` | passed |

## Claim boundary

- KHK metadata selects canonical response families; report text does not set pressure, temperature, opening size, enclosure geometry, heat flux or event timing.
- A passed trace means the mapped family can traverse process physics, virtual detection, safety logic and native consequence calculation where applicable.
- It does not reconstruct a KHK accident, validate physics or frequency, establish safe distance, or show that a response is correct or effective.
- The KOH electrolyte case is explicitly outside the gaseous-hydrogen model; liquid-hydrogen, production-equipment, explosion and valve-seat mechanisms remain bounded proxies.
