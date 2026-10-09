# API and monitoring interface

## Runtime layers

```text
Web monitor
    -> FastAPI job API
        -> ReferenceScenario factory
            -> SafeFullStationSimulator
                -> CoolProp + SciPy BDF
                -> Safety PLC and fault injection
                -> HyRAM+ runtime backend
```

The API runs simulations in a bounded two-worker thread pool. Long calculations do
not block health or job-status requests. Results remain in process memory for this
prototype; a production deployment should use persistent object storage and a job
queue.

## Installation and launch

```text
cd hydrogen-station-sim
python -m pip install -r requirements-api.txt
python -m h2station
```

Open `http://127.0.0.1:8000`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | CoolProp, solver, and HyRAM connection status |
| GET | `/api/evidence/local-station` | Privacy-bounded local station evidence coverage and claim boundary |
| GET | `/api/config/defaults` | Default scenario payload |
| POST | `/api/simulations` | Queue a dynamic simulation |
| GET | `/api/simulations/{id}` | Read progress or failure details |
| GET | `/api/simulations/{id}/result` | Retrieve summary and time series |

Inputs use user-facing MPa, degrees Celsius, g/s, and millimetres. The API converts
all values to SI before creating physical models.

## HyRAM configuration

When `hyram==6.1` is installed, the native adapter is loaded automatically. Outdoor
observation locations can be supplied as JSON through
`H2STATION_HYRAM_LOCATIONS`. Indoor releases require an explicit
`H2STATION_HYRAM_INDOOR_JSON` enclosure definition.

Alternatively, set an importable `module:function` evaluator:

```text
H2STATION_HYRAM_EVALUATOR=my_site.hyram_bridge:evaluate_release
```

The function receives `HyRAMDynamicReleaseRequest` and returns a mapping containing
the selected outdoor jet/plume/flame/overpressure or indoor accumulation results.
The existing `HyRAMAdapter` and `DynamicRiskCoordinator` should be assembled inside
that function. The request always includes the physics-derived
`mass_flow_override_kg_s`.

If neither a custom evaluator nor the HyRAM package can be loaded, the server remains
available but reports HyRAM as unconfigured. It preserves leak source terms and never
fabricates consequence or harm results.

## Monitoring interface

The responsive interface provides:

- Vehicle pressure, temperature, and density-based SOC
- Active cascade dispatch and recharge banks
- Bank pressures and dispenser flow animation
- ESD and HyRAM connection state
- Pressure, temperature, and mass-flow trends
- Timeline playback and event log
- Optional hose-leak fault scenario

The frontend polls only job state while a calculation runs, downloads the completed
result once, and performs timeline playback locally.

## Production boundary

This interface is an engineering simulator and monitoring prototype. It is not a
certified safety controller and must not directly command field equipment. A field
deployment requires authenticated APIs, role-based authorization, immutable audit
records, OPC UA or site gateway integration, cybersecurity review, and independent
functional-safety lifecycle evidence.
