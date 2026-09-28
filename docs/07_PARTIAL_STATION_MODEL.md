# Coupled partial-station dynamic model

## Implemented boundary

The partial-station model starts at the pressure-control-valve inlet and ends in a
Type IV vehicle tank:

```text
upstream supply -> PCV -> precooler -> hose line-pack -> nozzle/receptacle
                -> vehicle gas -> HDPE liner -> CFRP shell -> ambient
```

This follows the public H2FillS partial-station boundary while retaining a clean-room
implementation. H2FillS requires the cooling system to be downstream of the PCV on
the low-pressure side, which is also the topology used here.

## Dynamic states

The coupled model currently has eight differential states:

1. Precooler coolant/core temperature
2. Hose hydrogen mass
3. Hose hydrogen internal energy
4. Hose wall temperature
5. Vehicle hydrogen mass
6. Vehicle hydrogen internal energy
7. Vehicle liner temperature
8. Vehicle CFRP shell temperature

The supply pressure and temperature are time-dependent boundary inputs. A later
full-station model will replace that boundary with cascade-bank states.

## Pressure restrictions

PCV and nozzle flow are calculated as adiabatic real-gas restrictions. For each
upstream stagnation state, CoolProp supplies entropy, enthalpy, and density. SciPy
searches the physically available pressure interval for maximum isentropic mass
flux:

```text
G(p) = rho(p, s0) * sqrt(2 * (h0 - h(p, s0)))
mdot = Cd * A * opening * max(G)
```

Restricting the search to pressures between the actual downstream pressure and the
upstream pressure handles both unchoked and choked operation without an ideal-gas
critical-pressure-ratio assumption. The effective areas remain calibration inputs.

## Precooler

The hydrogen-side outlet temperature uses an effectiveness/NTU relation:

```text
epsilon = 1 - exp(-UA / (mdot * cp))
T_out = T_in - epsilon * (T_in - T_coolant)
```

CoolProp converts between pressure-temperature and pressure-enthalpy states, so the
model preserves throttling enthalpy and captures hydrogen's Joule-Thomson behavior.
The coolant/core temperature has finite thermal capacity and exchanges heat with a
chiller setpoint. This permits cold-start, heat-soak, and inadequate-chiller cases.

The 2024 precooling study confirms that heat-exchanger outlet temperature depends
strongly on inlet temperature and transient mass flow and that cooling strategy
affects energy consumption:
https://doi.org/10.1016/j.ijhydene.2024.04.064

## Hose line-pack

The hose is a fixed-volume mass and energy control volume:

```text
dm_h/dt = mdot_pcv - mdot_nozzle

dU_h/dt = mdot_pcv*h_cold - mdot_nozzle*h_h
          - UA_hw*(T_h - T_wall)

C_wall*dT_wall/dt = UA_hw*(T_h - T_wall)
                    - UA_wa*(T_wall - T_ambient)
```

This makes PCV outlet, hose, and receptacle states distinct. Published work reports
that hose, nozzle/receptacle, onboard pipe dimensions, and fitting flow coefficients
materially alter fill rate and final SOC:
https://doi.org/10.1016/j.ijhydene.2023.04.075

## Numerical coupling

The digital pressure-ramp controller is evaluated once per fixed controller period.
Its command is held while SciPy BDF integrates the eight physical states. This
prevents adaptive solver evaluations from changing controller memory or producing
noncausal valve commands.

## Validation output

`PartialStationTrajectory.validation_traces()` directly emits the canonical channel
schema introduced in `06_PUBLIC_SIMULATORS_AND_VALIDATION.md`, including:

- PCV inlet and outlet pressure/temperature
- Precooler outlet temperature and heat rate
- Hose and receptacle pressure/temperature
- Dispensed mass flow and injector velocity
- Vehicle gas, liner, liner/CFRP, and CFRP temperatures
- Vehicle pressure, SOC, and controller pressure reference

This channel selection follows the output list in the May 2024 H2FillS manual:
https://www.nrel.gov/docs/libraries/hydrogen/h2fills-user-manual.pdf

## Fitting variables

`DispenserFitParameters` exposes independent multipliers for PCV area, nozzle area,
pre-cooler UA and thermal capacity, chiller UA, hose volume, hose heat transfer, and
hose wall thermal capacity. Nominal physical dimensions remain separate from these
multipliers so fitted values can be audited.

## Important limitations

- The hose is one well-mixed cell. Additional finite volumes will be needed if
  measured delay or axial temperature gradients cannot be reproduced.
- PCV and nozzle are quasi-steady restrictions; mechanical actuator dynamics remain
  in the supervisory/component layer.
- The precooler currently uses one coolant/core temperature. A segmented wall-fluid
  model is the preferred refinement when exchanger geometry is available.
- The example values are illustrative and are not qualified station hardware data.
- No claim of SAE J2601 compliance is made without licensed schedule inputs and
  validation against the required hardware and test matrix.

## Next implementation step

Replace the prescribed supply boundary with dynamic low-, medium-, and high-pressure
cascade banks. Add bank-selection sequencing with configurable dead-time/overlap and
then connect compressor recharge without bypassing mass and energy conservation.

