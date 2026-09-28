# Public simulator benchmark and validation plan

## Decision

The implementation will use a clean-room Python model based on published governing
equations. Public simulators are used for architecture comparison and validation,
not as sources for copied code or proprietary fueling tables.

Validation will proceed in this order:

1. Thermophysical properties and isolated component balances
2. Partial station from dispenser breakaway to vehicle tank
3. Full station from ground storage through dispenser to vehicle
4. Repeated fills, cascade recharge, and simultaneous operating modes
5. Fault transients and HyRAM consequence/risk coupling

This order isolates errors in the filling line and vehicle model before compressor,
cascade scheduling, and station supervisory logic are introduced.

## Reference implementations

### NREL H2FillS

H2FillS is the strongest public comparison target for the fueling transient. Its
full-station model starts at high-pressure ground storage and ends at the vehicle;
its partial model starts at the dispenser breakaway. The May 2024 manual documents
series, parallel, multi-tank, ambient-fill, and defueling configurations.

Important comparison behavior:

- Pressure-ramp-rate and fuel-delivery-temperature inputs
- Uploaded time-dependent supply conditions
- Optimal APRR batch calculations
- Cooling-system outlet-temperature control
- Multi-tank vehicle configurations
- Density-based H35/H50/H70 SOC termination

H2FillS reports the channel set adopted in `h2station.validation.OutputChannel`,
including bank, PCV, heat exchanger, hose, receptacle, vehicle inlet, vehicle gas,
liner, CFRP, SOC, and injector quantities.

Source: https://www.nrel.gov/docs/libraries/hydrogen/h2fills-user-manual.pdf

### MathWorks hydrogen refueling station example

The current example provides a useful full-station control reference:

- 200 bar low-pressure storage
- Three-stage intercooled positive-displacement compressor
- 450/650/950 bar low/medium/high cascade buffers
- Lowest adequate pressure bank dispatched first
- Higher-pressure bank prioritized during recharge
- PI flow controller, PI precooler controller, and supervisory state machine
- Separate pressure-reduction valve, precooler, and vehicle subsystem

Its published results also expose an important switching transient: mass-flow spikes
can occur when changing cascade banks. Our valve sequencing must therefore include
overlap/dead-time as a configurable parameter rather than instantaneous ideal
switching.

Source: https://www.mathworks.com/help/hydro/ug/hydrogen-refueling-station.html

### DTU Hydrogen-Fuelling-Station Modelica library

The DTU repository is a public component-based Dymola/Modelica implementation and
uses CoolProp through ExternalMedia. It is valuable for comparing component and
connector boundaries. Its license is GPL-3.0, so no source code or fitted table data
will be copied into this implementation. Any future direct reuse requires an
explicit project licensing decision.

Repository: https://github.com/DTU-TES/Hydrogen-Fuelling-Station

License: https://github.com/DTU-TES/Hydrogen-Fuelling-Station/blob/master/LICENSE.txt

### Published cascade and control models

The 2021 cascade fast-fill study supports a lumped thermodynamic cascade model,
variable pressure switching, and joint optimization of switching pressure and
pre-cooling temperature.

Source: https://doi.org/10.1016/j.est.2021.102306

A 2025 study develops a multi-stage dynamic filling model and compares storage
configuration, compressor displacement, and compressor control strategies. It is
useful for later station-level sensitivity cases, but its reported optimum is not a
universal design default.

Source: https://doi.org/10.1016/j.ijhydene.2025.06.207

## Validation data contract

`h2station.validation` now provides:

- Canonical, unit-explicit names for dynamic output channels
- Source and case identifiers attached to every trace
- Strictly increasing time and finite-value checks
- Shape-preserving PCHIP alignment on the overlapping time interval
- NRMSE, mean error, maximum absolute error, and final error
- Per-channel acceptance criteria and an aggregate case result
- Independent integral mass-balance residual calculation

PCHIP is used instead of a high-order spline to avoid introducing artificial
oscillations around valve switching and flow discontinuities.

## Minimum benchmark cases

| Case | Conditions varied | Primary outputs |
|---|---|---|
| PT-01 | Initial pressure | Tank pressure, gas temperature, SOC |
| PT-02 | Soak/ambient temperature | Gas, liner, CFRP temperatures |
| PT-03 | APRR | Flow, pressure reference, final temperature |
| PT-04 | Delivery temperature | Heat duty, inlet temperature, final SOC |
| PT-05 | Line restriction | Hose/receptacle pressure and flow |
| FT-01 | Cascade initial pressures | Bank switching, flow spikes, utilization |
| FT-02 | Compressor capacity | Recharge time, bank readiness, energy |
| FT-03 | Repeated vehicles | Queue service, thermal recovery, availability |
| SF-01 | Leak during fill | Isolation time, released mass, HyRAM consequence |
| SF-02 | Cooling failure | Temperature trip and safe shutdown behavior |

## Acceptance criteria policy

Numerical tolerances are not scientific validation tolerances. Acceptance limits
must be assigned per measured quantity before viewing model errors and must record:

- Measurement uncertainty and sampling rate
- Sensor location and response time
- Test article geometry and material properties
- Boundary-condition uncertainty
- Whether a parameter was calibrated on the same case

Calibration and validation cases must be separated. A model fitted to one fill will
be judged primarily on withheld pressures, ambient temperatures, delivery
temperatures, and tank geometries.

## Next implementation step

The next code phase is the dispenser-line subsystem: PCV, finite-volume precooler,
breakaway/hose line-pack, nozzle/receptacle, and the new Type IV tank integrated in
one variable-state network. Its result object will emit the canonical channel names
defined here, after which the partial-station benchmark can be populated.

