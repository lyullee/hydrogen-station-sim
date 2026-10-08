# HIAD runtime response handoff audit

This audit executes one canonical fixture per mapped HIAD family and checks
the actual monitor → response-selection → staged-guidance path.

- Executable family fixtures: **9**
- Response handoffs passed: **9/9**

| Family | Result | Selected response family | Guidance stages |
| --- | --- | --- | --- |
| `gas_release` | `passed` | `gas_release`, `gas_release`, `gas_release`, `gas_release`, `gas_release`, `gas_release`, `gas_release` | `yes` |
| `hydrogen_fire` | `passed` | `hydrogen_fire`, `gas_release`, `external_fire`, `gas_release`, `gas_release`, `gas_release`, `gas_release`, `gas_release`, `gas_release` | `yes` |
| `hose_connection` | `passed` | `gas_release`, `gas_release`, `gas_release`, `gas_release`, `gas_release`, `gas_release`, `gas_release` | `yes` |
| `overpressure` | `passed` | `overpressure`, `overpressure`, `overpressure` | `yes` |
| `precooling_fault` | `passed` | `precooling_fault` | `yes` |
| `fueling_fault` | `passed` | `low_supply_or_blockage`, `low_supply_or_blockage`, `low_supply_or_blockage`, `low_supply_or_blockage`, `low_supply_or_blockage`, `low_supply_or_blockage` | `yes` |
| `compressor_thermal` | `passed` | `external_fire`, `external_fire` | `yes` |
| `external_fire` | `passed` | `external_fire`, `external_fire` | `yes` |
| `isolation_failure` | `passed` | `fueling_fault`, `fueling_fault`, `fueling_fault`, `low_supply_or_blockage`, `low_supply_or_blockage` | `yes` |

## Claim boundary

- The public HIAD inventory does not provide synchronized boundary traces; canonical fixtures are used for runtime testing.
- The audit checks monitor-frame availability, response-family selection, structured guidance and complete recognition/immediate/stabilize/restart/prevention stages.
- It does not infer incident parameters from public narratives or establish that any response action is correct or effective in the field.
