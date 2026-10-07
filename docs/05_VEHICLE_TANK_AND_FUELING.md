# Vehicle tank and fueling-control model

## Scope

This phase adds a Type IV vehicle-tank model and a fueling-controller interface.
It does not copy the proprietary SAE J2601 fueling tables. An authorized table
implementation, MC Formula implementation, or station supervisory controller must
supply the target pressure, APRR, delivery temperature, and maximum mass flow.

## Three-zone Type IV tank

The model has four dynamic states:

1. Hydrogen mass, `m_g`
2. Hydrogen internal energy, `U_g`
3. Mean HDPE liner temperature, `T_l`
4. Mean CFRP shell temperature, `T_s`

CoolProp closes the real-gas state from density and specific internal energy:

```text
rho_g = m_g / V_eff
u_g   = U_g / m_g
(p_g, T_g, h_g) = CoolProp(rho_g, u_g)
```

The conservation equations are:

```text
dm_g/dt = m_in - m_out

dU_g/dt = m_in*h_in - m_out*h_g - UA_gl*(T_g - T_l)

C_l*dT_l/dt = UA_gl*(T_g - T_l) - UA_ls*(T_l - T_s)

C_s*dT_s/dt = UA_ls*(T_l - T_s) - UA_sa*(T_s - T_amb)
```

The fixed-volume assumption is appropriate for the first implementation. The
effective-volume multiplier is exposed so that small compliance and geometric
uncertainty can be fitted without changing the conservation model.

## Calibration parameters

`CompositeTankFitParameters` keeps fitting variables separate from traceable
physical inputs:

| Parameter | Meaning | Suggested prior |
|---|---|---:|
| `effective_volume_multiplier` | Geometric/compliance correction | 1.0 before a validated fit |
| `gas_liner_ua_multiplier` | Gas-to-liner effective convection | 1.0 before a validated fit |
| `liner_shell_ua_multiplier` | Liner/CFRP contact conduction | 1.0 |
| `shell_ambient_ua_multiplier` | External convection/radiation aggregate | 1.0 |
| `liner_heat_capacity_multiplier` | Liner effective thermal mass | 1.0 |
| `shell_heat_capacity_multiplier` | CFRP effective thermal mass | 1.0 |

Fit the heat-transfer multipliers first against pressure, gas-temperature, liner,
and shell-temperature histories. Fit effective volume only when tank-volume and
sensor calibration uncertainty have been independently assessed.

### Current runtime profile

The normal API default uses `vehicle_tank_calibration=public_type_iv`. It applies
the frozen public Type-IV fit in
[`research/tank_model_validation_v2.json`](../research/tank_model_validation_v2.json):

| Quantity | Runtime value |
|---|---:|
| effective-volume multiplier | 1.0527292612 |
| gas-to-liner UA multiplier | 31.4606565193 |

The fit was calibrated on 23 and evaluated on 12 held-out public fills with
measured mass-flow and inlet-temperature boundaries. It improves only the
vehicle-tank surrogate. It does not calibrate or validate the compressor,
cascade topology, dispenser, station controller, safety distance, or a specific
vehicle. Set `vehicle_tank_calibration=reference` for the uncalibrated 1.0/1.0
sensitivity configuration. The runtime/recheck linkage is recorded without raw
experimental rows in
[`research/public_type_iv_tank_runtime_calibration_2026_10_07.json`](../research/public_type_iv_tank_runtime_calibration_2026_10_07.json).

## Fueling protocol interface

`FuelingSchedule` is the boundary between the public physics model and a compliant
fueling-protocol implementation. The sampled controller generates a pressure ramp,
applies a PI valve command, caps mass flow, and independently terminates on target
pressure, density-based SOC, or maximum gas temperature.

SOC uses the density ratio:

```text
SOC = rho(p, T) / rho(NWP, 288.15 K)
```

The default maximum gas temperature is 358.15 K (85 degC). This is a safety stop,
not a substitute for the complete SAE J2601 station/tank qualification process.

## Numerical coupling

The controller is sampled at a fixed period and its command is held during each
integration segment. Each segment is solved with SciPy `solve_ivp(method="BDF")`.
This avoids updating a stateful digital controller at the solver's internal,
adaptive evaluation points.

## Literature basis

- Xiao et al., *International Journal of Hydrogen Energy* (2024), comparison of
  single-, dual-, and triple-zone compressed-hydrogen tank models:
  https://doi.org/10.1016/j.ijhydene.2023.06.081
- Type IV 36.9 L tank experiments and validation of a one-dimensional thermal
  model: https://doi.org/10.1016/j.ijhydene.2015.05.157
- Additional Type IV fast-fill thermal modeling and experimental validation:
  https://doi.org/10.1016/j.ijhydene.2015.06.114
- NREL H2FillS model and user manual, including pressure-ramp and SOC termination
  concepts: https://www.nrel.gov/hydrogen/h2fills
- SAE J2601 official scope and current standard entry:
  https://saemobilus.sae.org/standards/j2601_202005-fueling-protocols-light-duty-gaseous-hydrogen-surface-vehicles
- Public SAE overview describing the 85 degC compressed-storage temperature limit:
  https://www.sae-j2601.com/wp-content/uploads/2021/01/SAE-J2601-The-Worldwide-Standard-for-Hydrogen-Fueling-Stations.pdf
- Representative Type IV material properties used as starting estimates:
  https://pure.ulster.ac.uk/ws/files/71364550/HE_25075_edit_report.pdf

## Current limitations and next connection

- The gas zone is spatially uniform, so it predicts mass-averaged temperature, not
  local hot spots near the inlet or liner surface.
- `gas_liner_ua_w_k` is currently an effective parameter. A later revision should
  calculate it from jet mixing and natural/forced convection correlations.
- The example inlet is intentionally only a configuration demonstration. The next
  integration step is to connect the existing CoolProp real-gas restriction, hose
  line-pack model, cascade banks, and precooler to `CompositeTankFillSimulator`.
- Full J2601 conformance requires licensed table/MC Formula inputs, station hardware
  limits, communications behavior, fault handling, and validation test evidence.
