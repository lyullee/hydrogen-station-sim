# Cascade storage and compressor integration

## Implemented full-station boundary

The dynamic model now spans:

```text
compressor suction boundary -> multistage compressor -> cascade banks
                                                   -> selected bank -> PCV
-> precooler -> hose -> nozzle/receptacle -> Type IV vehicle tank
```

Three cascade banks and the partial station are integrated in one BDF state vector.
Each bank contributes hydrogen mass, hydrogen internal energy, and wall temperature,
giving 17 continuous states for a three-bank station.

## Cascade storage model

Each bank uses the fixed-volume real-gas balances:

```text
dm/dt = mdot_compressor - mdot_dispenser

dU/dt = mdot_compressor*h_compressor
        - mdot_dispenser*h_bank
        - UA_gw*(T_gas - T_wall)

C_wall*dT_wall/dt = UA_gw*(T_gas - T_wall)
                    - UA_wa*(T_wall - T_ambient)
```

CoolProp closes every bank state from density and specific internal energy. Bank
volume, wall capacity, and both heat-transfer paths have explicit fitting
multipliers.

## Supervisory control

At each fixed control interval:

- Dispatch selects the lowest pressure-class bank that exceeds hose pressure by a
  configurable margin.
- Recharge excludes the dispatch bank and prioritizes the highest pressure-class
  bank below its target pressure.
- The selected decisions remain fixed during the following adaptive BDF segment.
- If no bank has adequate pressure, PCV inflow is disabled while residual hose gas
  can continue entering the vehicle.

This follows the public MathWorks station logic: lowest adequate bank first during
dispensing and higher-pressure storage first during recharge.

Reference: https://www.mathworks.com/help/hydro/ug/hydrogen-refueling-station.html

## Compressor model

The positive-displacement compressor mass flow starts from suction density:

```text
mdot = rho_suction * swept_volume_rate * volumetric_efficiency
```

Equal pressure ratio is assigned to each stage. CoolProp calculates the real-gas
isentropic outlet enthalpy, and actual stage work is obtained from the stage
isentropic efficiency:

```text
h_out = h_in + (h_out_s - h_in) / eta_is
```

Intermediate stages return to a configured intercooler outlet temperature. Total
electrical power includes mechanical and motor efficiencies. Flow, isentropic
efficiency, and power multipliers are isolated for later manufacturer-map fitting.

Recent dynamic HRS literature likewise uses equal stage pressure ratios,
intercooling near ambient, volumetric displacement, and summed stage work:
https://doi.org/10.1016/j.ijhydene.2026.153374

The DOE H2A delivery framework is retained as a later station energy and economic
cross-check, not as the transient solver:
https://www.hydrogen.energy.gov/program-areas/systems-analysis/h2a-analysis/h2a-delivery

## Outputs

`FullStationTrajectory` records:

- Pressure and temperature of every cascade bank
- Compressor mass flow and electrical power
- Selected dispatch and recharge bank at every control sample
- Dispenser flow, PCV inlet, precooler, hose, vehicle, liner, shell, and SOC channels
- Fueling phase and stop reason

## Known limitations

- Compressor cylinder pulsation, clearance-volume dynamics, leakage, valve motion,
  and manufacturer maps are not yet modeled.
- Intercoolers are currently quasi-steady temperature boundaries; their thermal
  capacitance will be added when measured cooldown data are available.
- Bank valves switch discretely at control boundaries. Actuator travel, dead time,
  overlap, check-valve dynamics, and switching-flow spikes are the next refinement.
- The compressor suction is currently a pressure-temperature boundary. A low-pressure
  buffer, trailer, pipeline, or electrolyzer model can replace it without changing
  the compressor equations.
- The example values are illustrative and are not validated equipment data.

## Validation target

The 2024 whole-station study covers storage-to-vehicle, compressor-to-vehicle, and
compressor-to-station-storage operating modes and reports comparison with application
data. It will be used to define the next withheld full-station validation cases:
https://doi.org/10.1016/j.est.2024.110508

