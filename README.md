# Hydrogen Station Dynamic Simulator

Physics-first Python simulator for gaseous hydrogen refueling stations. The existing
Java/browser simulator is a visual reference only; this package has an independent
model, API, and monitoring interface.

## Implemented system

- CoolProp real-gas hydrogen properties
- Storage mass, energy, and wall-temperature dynamics
- Three-stage compressor with intercooling and electrical power
- Three-bank cascade dispatch and recharge
- Real-gas PCV, nozzle, check valve, and relief primitives
- Finite-UA precooler and finite-volume hose line-pack
- Gas, HDPE liner, and CFRP Type IV vehicle tank
- External SAE J2601-compatible APRR schedule boundary
- Sampled normal control and independent latched safety PLC
- Sensor, actuator, cooling, compressor, E-stop, and leak faults
- Leak mass and enthalpy feedback to the physical inventory
- HyRAM+ 6.1 outdoor and optional indoor consequence bridge
- FastAPI simulation jobs and responsive monitoring UI
- H2FillS-compatible validation channels and metrics

Internal units are SI. The API accepts MPa, degrees Celsius, g/s, and millimetres and
converts them at the boundary.

## Installation

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[api]"
```

Include HyRAM+ when its GPL-3.0 licensing is appropriate for the deployment:

```powershell
.venv\Scripts\python -m pip install -e ".[all]"
```

## Run

```powershell
.venv\Scripts\h2station
```

Open `http://127.0.0.1:8000`.

## HyRAM configuration

When `hyram==6.1` is installed, the native adapter is selected automatically. Default
outdoor observation points are 1 m, 3 m, and 5 m downstream at 1.5 m elevation.
Override them with JSON:

```powershell
$env:H2STATION_HYRAM_LOCATIONS='[[1,0,1.5],[5,0,1.5]]'
```

Indoor accumulation requires an explicit enclosure definition through
`H2STATION_HYRAM_INDOOR_JSON`; no enclosure geometry is invented. A site-specific
backend can instead be selected with
`H2STATION_HYRAM_EVALUATOR=module:function`.

## Engineering status

This is a modeling and monitoring prototype, not a certified controller. Reference
scenario dimensions and thermal parameters are illustrative until calibrated against
traceable equipment and test data. SAE J2601 tables remain licensed external inputs.
The complete modeling basis, literature, limitations, and validation plan are in
`docs/`.
