# Hydrogen property table runtime

## Purpose

The process simulator uses one fluid: normal hydrogen. Repeated CoolProp calls from
adaptive BDF residual and numerical-Jacobian evaluations dominated runtime, so the
online process path now uses a generated property table. CoolProp HEOS remains the
offline reference used to regenerate the table. HyRAM is an independent consequence
engine and may continue to use its own CoolProp dependency internally.

## Table domain

- Pressure: 0.01 to 120 MPa, 321 logarithmically spaced points
- Temperature: 60 to 700 K, 421 linearly spaced points
- Density: 0.001 to 100 kg/m3, 321 logarithmically spaced points
- Fluid: CoolProp `Hydrogen`
- Stored properties: P, T, density, u, h, s, cp, cv, viscosity, conductivity,
  compressibility factor, and speed of sound

The P-T table supports direct states plus P-h and P-s inversion. A separate rho-T
surface supports rho-u inversion required by conserved vessel and hose states.
Queries outside the generated domain fail explicitly rather than silently
extrapolating.

## Runtime behavior

`h2station.tabulated.PropsSI` implements the scalar input/output combinations used by
the station model. `HydrogenEOS` uses the same singleton table. Bounded LRU caches use
exact floating-point state keys, avoiding quantization and preserving deterministic
results while eliminating duplicate evaluations from BDF Jacobian construction.

## Regeneration

Install the table-generation dependency and run:

```powershell
python -m pip install -e ".[table-build]"
python scripts/generate_hydrogen_table.py
```

The generated artifact is:

```text
src/h2station/data/hydrogen_properties_v1.npz
```

## Measured accuracy and performance

A fixed random sample of 200 states over 0.1-100 MPa and 220-450 K was compared
against CoolProp. Maximum relative errors were 0.0115% for density, 0.0021% for
enthalpy, 0.00046% for internal energy, and 0.00044% for cp. Fifty rho-u recovery
states showed maximum errors of 0.0475% in pressure and 0.0010% in temperature.

On the local reference machine, a two-second fast-mode station simulation decreased
from 4.16 seconds with direct property calls to 0.39 seconds after table loading and
exact-state caching. Startup loads and decompresses the table once per server process.

A separate 30-second fast-mode station run completed in 3.33 seconds and emitted
31 live frames, corresponding to approximately 9.0 simulated seconds per wall-clock
second on the development host. Actual timing depends on CPU, scenario stiffness,
faults, and active HyRAM consequence evaluations.

## Engineering limitation

The table is an interpolation surrogate for the selected CoolProp version, not a new
equation of state. Validation data, table version, domain, interpolation error, and
generator version must be controlled together for engineering use. Extend and
regenerate the table before introducing states outside the documented envelope.
