# HIAD event-category concordance (2026-10-11)

This artifact compares coarse public HIAD outcome metadata with the already frozen digital-twin replay family IDs. It is a traceability check, not accident reconstruction.

- Cases joined: **34**
- Category match: **34**
- Partial: **0**
- Metadata/runtime conflict: **0**
- Integration traces passing: **34 / 34**

## Mapping contract

| Public physical-effect category | Required runtime family | Prohibited runtime family |
| --- | --- | --- |
| Unignited Hydrogen Release | `gas_release` | `hydrogen_fire` |
| Hydrogen release and ignition | `gas_release`, `hydrogen_fire` | — |
| No Hydrogen Release | — | `gas_release`, `hydrogen_fire` |

## Event concordance

| Event | Public effect | Public consequence | Runtime recipes | Representation | Result |
| --- | --- | --- | --- | --- | --- |
| 396 | Unignited Hydrogen Release | Leak no ignition | `gas_release` | direct_physical_replay | matched |
| 401 | Unignited Hydrogen Release | Leak no ignition | `gas_release` | direct_physical_replay | matched |
| 402 | No Hydrogen Release | Near miss | `compressor_thermal` | proxy_partial_replay | matched |
| 403 | Unignited Hydrogen Release | Leak no ignition | `gas_release`, `fueling_fault` | direct_physical_replay | matched |
| 404 | No Hydrogen Release | Near miss | `fueling_fault` | direct_physical_replay | matched |
| 411 | No Hydrogen Release | Near miss | `compressor_thermal` | proxy_partial_replay | matched |
| 454 | No Hydrogen Release | near miss | — | response_only_no_physical_model | matched |
| 463 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `fueling_fault` | direct_physical_replay | matched |
| 702 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `hose_connection` | direct_physical_replay | matched |
| 803 | No Hydrogen Release | Near miss | `fueling_fault` | direct_physical_replay | matched |
| 884 | Hydrogen release and ignition | Explosion | `hydrogen_fire`, `gas_release`, `overpressure` | direct_physical_replay | matched |
| 953 | Unignited Hydrogen Release | Leak no ignition | `gas_release` | direct_physical_replay | matched |
| 1038 | No Hydrogen Release | near miss | `hose_connection`, `precooling_fault` | direct_physical_replay | matched |
| 1062 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `overpressure` | direct_physical_replay | matched |
| 1063 | Unignited Hydrogen Release | leak no ignition | `gas_release` | direct_physical_replay | matched |
| 1064 | Unignited Hydrogen Release | near miss | `gas_release` | direct_physical_replay | matched |
| 1106 | Hydrogen Release and Ignition | Explosion | `hydrogen_fire`, `gas_release` | direct_physical_replay | matched |
| 1159 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `overpressure` | direct_physical_replay | matched |
| 1161 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `overpressure` | direct_physical_replay | matched |
| 1163 | Hydrogen Release and Ignition | fire | `hydrogen_fire`, `gas_release`, `overpressure` | direct_physical_replay | matched |
| 1173 | Hydrogen Release and Ignition | explosion followed by a fire | `hydrogen_fire`, `gas_release`, `overpressure` | direct_physical_replay | matched |
| 1191 | Hydrogen Release and Ignition | fire | `hydrogen_fire`, `gas_release`, `overpressure` | direct_physical_replay | matched |
| 1193 | Unignited Hydrogen Release | leak no ignition | `gas_release` | direct_physical_replay | matched |
| 1194 | Unignited Hydrogen Release | leak no ignition | `gas_release` | direct_physical_replay | matched |
| 1195 | Unignited Hydrogen Release | leak no ignition | `gas_release` | direct_physical_replay | matched |
| 1196 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `hose_connection` | direct_physical_replay | matched |
| 1198 | Hydrogen Release and Ignition | explosion | `hydrogen_fire`, `gas_release`, `hose_connection` | direct_physical_replay | matched |
| 1202 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `hose_connection` | direct_physical_replay | matched |
| 1203 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `compressor_thermal` | proxy_partial_replay | matched |
| 1204 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `hose_connection` | direct_physical_replay | matched |
| 1205 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `compressor_thermal` | proxy_partial_replay | matched |
| 1206 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `hose_connection` | direct_physical_replay | matched |
| 1207 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `fueling_fault` | direct_physical_replay | matched |
| 1208 | Unignited Hydrogen Release | leak no ignition | `gas_release`, `fueling_fault` | direct_physical_replay | matched |

## Limits

The public incident narrative and emergency-action text are not used as model inputs. A match only means the declared coarse family contract is consistent. It does not validate event frequency, numerical consequence magnitude, field safety distance, operator benefit, ethics, or human effectiveness.

Source HIAD SHA-256: `27b7fc752fe7ad706eb48854447bb203605be30b745515a259fad89325cc2536`
Source replay SHA-256: `77812ae1df3df20e637ca9ba508064790e219db2e0190e866572ee320dbb87c8`
