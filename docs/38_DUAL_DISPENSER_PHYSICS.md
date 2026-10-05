# Dual-dispenser station model

## Scope

Added a second H70 dispensing point as a coupled physical subsystem rather than a decorative duplicate.

## Physical structure

- Each dispenser has its own sampled fueling controller and pressure-ramp command.
- Each dispenser has independent PCV restriction flow, finite precooler coolant state, chiller heat rejection, hose line-pack mass/internal energy, hose wall temperature, nozzle restriction and composite vehicle tank state.
- Both dispensers draw from the same low/medium/high cascade bank states.
- When both points dispatch from one bank, both PCV outlet mass flows are summed in that bank's mass and enthalpy balance.
- Each point has an independent break-before-make cascade valve sequencer. A bank serving either dispenser is excluded from simultaneous compressor recharge selection.
- The compressor and three storage banks remain common station equipment.
- The station-wide safety PLC receives the maximum of both vehicle pressures and temperatures, maximum hose pressure/temperature, and summed PCV/nozzle flows. A trip closes both PCVs and both cascade paths.
- HyRAM fault/consequence monitoring remains station-wide. API fault targets `dispenser_2.hose` and `vehicle_2.tank` resolve to the second subsystem and remove mass and enthalpy from that state. The existing checkbox remains associated with the primary hose; a second selector is not yet exposed in the UI.

## API compatibility and new channels

Legacy pcv_flow_g_s and nozzle_flow_g_s now represent station totals.

New live/result channels:

- vehicle_2_pressure_mpa
- vehicle_2_temperature_c
- vehicle_2_soc_percent
- pcv_1_flow_g_s, pcv_2_flow_g_s
- nozzle_1_flow_g_s, nozzle_2_flow_g_s
- hose_2_pressure_mpa, hose_2_temperature_c

New input fields:

- initial_vehicle_2_pressure_mpa
- initial_vehicle_2_temperature_c
- target_vehicle_2_pressure_mpa
- vehicle_geometry_basis (`reference` by default or opt-in `capacity_eos`)
- vehicle_capacity_kg and vehicle_2_capacity_kg when `capacity_eos` is selected

## Monitoring and 3D

- The control strip accepts separate initial pressures for vehicles 1 and 2.
- KPI cards display vehicle 2 pressure, temperature and SOC as secondary readings.
- The process view reports the split nozzle flow.
- The former visual-only second dispenser is connected to the common fueling header.
- A second detailed FCEV, hose and nozzle are placed at dispenser 2.
- Dispenser 2 screen and equipment card use vehicle 2 live values.
- Vehicle cutaway mode applies to both vehicles.

## Standards and references

- SAE J2601_202005 defines light-duty gaseous-hydrogen fueling process limits, including delivery temperature, maximum flow, pressure ramp and end pressure: https://saemobilus.sae.org/standards/j2601_202005-fueling-protocols-light-duty-gaseous-hydrogen-surface-vehicles
- H2Tools explains cascade bank switching and the non-linear pressure/density constraints of H70 transfer: https://h2tools.org/faq/tank-filling

This implementation gives each point an independent instance of the existing physics-first fueling model. It does not claim certification to SAE J2601, dispenser listing, station capacity approval or simultaneous-fueling validation.

## Validation

No tests, syntax checks, browser execution or post-edit inspection were performed. Runtime validation and quantitative simultaneous-fill verification remain outstanding.
