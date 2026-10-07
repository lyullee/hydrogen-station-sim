# Cascade storage and compressor integration

## Implemented full-station boundary

The dynamic model now spans:

```text
compressor suction boundary -> multistage compressor -> cascade banks
                                                   -> finite common header -> PCV 1/2
-> precooler -> hose -> nozzle/receptacle -> Type IV vehicle tank
```

Three cascade banks, the common high-pressure header, two dispenser trains and two
vehicle tanks are integrated in one state vector. Each bank and the header contribute
hydrogen mass, hydrogen internal energy and wall temperature. The dual-dispenser
reference station therefore has 28 continuous states.

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

## Finite common-header model

The cascade selector valves feed a separate 0.015 m³ reference header. Its reference
bank-to-header restriction area is 6.0e-6 m². These are declared prospective geometry
values rather than fitted or manufacturer-specific data. The startup header pressure
is initialized to the low-bank pressure; continued runs preserve the actual residual
header state.

The header uses the same real-gas fixed-volume closure as the banks:

```text
dm_header/dt = sum(mdot_bank_to_header) - sum(mdot_header_to_pcv) - mdot_leak

dU_header/dt = sum(mdot_in*h_source) - sum(mdot_out*h_header)
                  - UA_gw*(T_header - T_wall) - mdot_leak*h_header
```

Bank-to-header flow is a signed real-gas restriction flow. Normal check-valve logic
sets reverse flow to zero. An explicit `check-valve-failure` on target `header`
enables reverse transfer and applies equal and opposite mass and enthalpy terms to
the affected bank and header. If two dispensers select the same bank, the shared
selector path is represented once at the larger opening command.

The HAZOP channels now use this physical state:

- `PT-1001`: common-header pressure
- `TT-1001`: common-header gas temperature
- `FT-1001`: signed total bank-to-header inflow
- `MASS_HEADER`: common-header hydrogen mass

This makes the common-header reverse-flow rule `HZ-073` and dynamic mass-balance
rule `HZ-074` executable. It also makes a `header` leak deplete the header inventory
instead of removing mass from the high bank proxy.

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

- The HAZOP workbook's stage-discharge temperature thresholds (45/60 degC,
  `HZ-019/020`, `HZ-027/028`, and `HZ-035/036`) are `PROPOSED` and not site
  activated. They are retained unchanged for traceability, but the simulator
  evaluates them only during a compressor thermal or matching temperature
  sensor-fault exercise. Normal pre-intercooler compression temperature is not
  treated as an accident. Production use requires approved OEM/site limits.

- Compressor cylinder pulsation, clearance-volume dynamics, leakage, valve motion,
  and manufacturer maps are not yet modeled.
- Intercoolers are currently quasi-steady temperature boundaries; their thermal
  capacitance will be added when measured cooldown data are available.
- Bank selector commands update at control boundaries; actuator travel and
  break-before-make dead time are modeled, while mechanical valve inertia and
  high-frequency pressure pulsation are not.
- Header geometry and restriction area are prospective reference values. They must
  remain fixed for a future apparatus-resolved holdout; the current implementation
  is prospective infrastructure, not external validation evidence.
- The compressor suction is currently a pressure-temperature boundary. A low-pressure
  buffer, trailer, pipeline, or electrolyzer model can replace it without changing
  the compressor equations.
- The example values are illustrative and are not validated equipment data.

## Validation target

The 2024 whole-station study covers storage-to-vehicle, compressor-to-vehicle, and
compressor-to-station-storage operating modes and reports comparison with application
data. It will be used to define the next withheld full-station validation cases:
https://doi.org/10.1016/j.est.2024.110508
