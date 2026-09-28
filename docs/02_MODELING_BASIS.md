# Modeling Basis

## Reference topology

The baseline gaseous H70 station is represented as:

```text
delivery/source storage
  -> multistage compressor and intercoolers
  -> low / medium / high cascade storage
  -> priority and flow-control restrictions
  -> hydrogen precooler
  -> hose and vehicle storage
```

Production, purification, tube-trailer manifold dynamics, liquid hydrogen,
cryopumps, vaporizers, and electrolyzers are future topology variants, not hidden
assumptions in the baseline.

## State variables and conservation equations

Each lumped vessel stores hydrogen mass `m`, total hydrogen internal energy `U`,
and wall temperature `Tw`.

```text
dm/dt = sum(mdot_in) - sum(mdot_out)

dU/dt = sum(mdot_in * h_in)
        - sum(mdot_out * h_tank)
        + UA_gw * (Tw - Tg)

Cw * dTw/dt = UA_gw * (Tg - Tw) + UA_wa * (Tamb - Tw)
```

CoolProp closes the state from `rho = m/V` and `u = U/m`. Pressure and
temperature are outputs, not separately integrated states. This avoids an
ideal-gas closure and preserves energy consistency.

## Restriction and valve flow

The restriction assumes adiabatic, isentropic acceleration from stagnation
state to a candidate throat pressure. At each candidate pressure CoolProp solves
`(p, s0)` and the mass flux is:

```text
G = rho * sqrt(2 * (h0 - h))
```

SciPy bounded optimization selects the maximum physically accessible flux between
downstream and upstream pressure. This naturally detects choking. The final flow
is `mdot = Cd * A_effective * G`. `Cd` and the opening characteristic are fitting
parameters; the equation of state is not fitted.

## Compressor

Each stage uses an isentropic reference outlet at the stage discharge pressure:

```text
h_out = h_in + (h_out,s - h_in) / eta_is
power = mdot * (h_out - h_in) / eta_mech
```

Equal pressure ratio is the baseline staging rule. Interstage cooling uses an
effectiveness relation. Positive-displacement mass flow scales with speed,
volumetric efficiency, and suction density. A manufacturer map can replace this
law without changing the network interface.

## Precooler

The baseline is a quasi-steady finite-UA model:

```text
T_out = T_coolant + (T_in - T_coolant) * exp(-UA / (mdot * cp))
```

Later versions may add coolant and metal thermal states and use `ht` correlations
for geometry-specific UA. The pressure drop remains a separate connection model.

## Numerical integration

The network converts every vessel to three ODE states and assembles enthalpy flow
at each connection. SciPy `solve_ivp` with BDF is the default because valve flow
and wall thermal inertia can create stiff time scales. Solver tolerances are
configuration, never fitting variables.

## Finite-volume station piping and hose

Each physical line is divided into configurable gas control volumes. Every cell
uses the same conserved mass and energy formulation as a vessel, with its own
pipe-wall thermal state. Face mass flow uses the complete isothermal compressible
pipe equation from `fluids`, with CoolProp average density and viscosity. Darcy
friction is iterated because Reynolds number depends on mass flow.

```text
fd = friction_factor(Re, roughness / diameter)
mdot = isothermal_gas(rho_avg, fd, p_up, p_down, length, diameter)
```

Minor losses are converted to an equivalent face friction contribution. An
isentropic real-gas nozzle calculation limits the result during a large pressure
step, preventing a friction relation from exceeding the inviscid choked-flow
bound. The face equations are quasi-steady; line-pack and thermal states are
dynamic. A momentum-state finite-volume option is reserved for wave-speed and
fast ESD studies.

## Valve actuation

Commanded and actual valve opening are separate. Actual position is integrated
with opening/closing time constants, asymmetric stroke-rate limits, deadband, and
a fail-safe position. Loss of actuator availability drives the valve toward its
declared fail-safe state. Mechanical stiction and hysteresis require valve test
data and are not enabled by an arbitrary default.

## Fitting parameter policy

| Module | Physical/design inputs | Fit candidates | Do not fit by default |
|---|---|---|---|
| Tank | volume, area, wall heat capacity | gas-wall HTC multiplier, ambient HTC multiplier | EOS |
| Restriction | bore/seat area, characteristic | discharge coefficient, area multiplier, rangeability | upstream state |
| Compressor | stages, speed, pressure limit | isentropic efficiency, volumetric efficiency, flow multiplier, mechanical efficiency | conservation equations |
| Precooler | coolant temperature, nominal UA | UA multiplier | hydrogen properties |
| Pipe | length, diameter, roughness, wall layers | roughness/HTC multipliers within justified bounds | geometry with drawings available |
| Valve actuator | stroke direction, fail-safe state | opening/closing time constants, rate limits, deadband | demanded position |
| HyRAM | leak diameter, angle, location, method | scenario uncertainty inputs | process pressure/temperature snapshot |

Every fitted value must eventually carry source, prior/bounds, dataset ID,
objective function, residual diagnostics, and validity range. A good numerical fit
outside the parameter's physical range is a model failure, not a calibration
success.

## Known limitations of this baseline

- The vessel is spatially uniform; no stratification or axial gradients.
- Restriction flow is one-dimensional and adiabatic.
- Pipe line-pack, friction, fittings, wall inertia, and hose dynamics are not yet
  represented.
- Compressor rotor/actuator and casing thermal dynamics are not yet represented.
- Precooler metal and coolant inventories are not yet dynamic.
- No SAE J2601 table/control implementation is included yet.
- HyRAM calculations are integrated at the software interface, but results remain
  scenario consequences until frequency and exposure models are supplied.
- No experimental validation claim is made for the current code.
