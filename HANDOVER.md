# Hydrogen Station Dynamic Simulator - Project Handover

Updated: 2026-09-20

## 1. What this project is

`hydrogen-station-sim` is an independent Python project for a physics-first dynamic simulator of a gaseous hydrogen refueling station. It was created separately from the legacy Java/Spring project; the Java browser simulator was used only as a visual reference.

The intended build order is:

1. First-principles component models
2. Whole-station dynamic simulation and safety layer
3. FastAPI service and simulation monitoring API
4. Browser monitoring UI and 3D operational view

This is a research and monitoring prototype. It is not a certified controller, a safety instrumented system, or a release-ready engineering calculation package.

## 2. Project location and transfer scope

Current project root:

```text
C:\path\to\hydrogen-station-sim
```

Transfer the full project folder, including `src`, `web`, `docs`, `tests`, `examples`, `scripts`, `README.md`, `pyproject.toml`, and this file.

Do not rely on these local/generated folders when moving accounts or machines:

- `.venv` - recreate it on the new machine
- `.idea` - PyCharm local configuration
- `.pytest_cache` - test cache only

## 3. Quick start on a new account or computer

Use Python 3.12 where possible. The package supports Python 3.10+, but the currently prepared environment used Python 3.12.

```powershell
cd C:\path\to\hydrogen-station-sim
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[api]"
.venv\Scripts\h2station
```

Open the monitoring UI at:

```text
http://127.0.0.1:8000
```

For native HyRAM+ 6.1 consequence calculations, install the optional dependency only when GPL-3.0 licensing is appropriate:

```powershell
.venv\Scripts\python -m pip install -e ".[all]"
```

In PyCharm:

1. Open the `hydrogen-station-sim` folder as the project root.
2. Select `.venv\Scripts\python.exe` as the project interpreter.
3. Create a Python run configuration using `src\h2station\__main__.py`, or run `.venv\Scripts\h2station` from the PyCharm terminal.
4. Keep the working directory at the project root, not `src\h2station`.

## 4. Runtime entry points

| Purpose | Location |
| --- | --- |
| Command-line startup | `src/h2station/cli.py` |
| Python module startup | `src/h2station/__main__.py` |
| FastAPI service | `src/h2station/api.py` |
| Main dashboard | `web/index.html` |
| Dashboard behavior | `web/app.js` |
| 3D station scene | `web/station3d.js` |
| 3D styles | `web/station3d.css` |

The server exposes these core interfaces:

| Interface | Purpose |
| --- | --- |
| `GET /api/health` | Service and safety backend readiness |
| `GET /api/config/defaults` | Default UI/simulation configuration |
| `POST /api/simulations` | Create an asynchronous simulation job |
| `GET /api/simulations/{job_id}` | Poll job state and progress |
| `GET /api/simulations/{job_id}/result` | Fetch completed results |
| `WS /api/simulations/{job_id}/stream` | Receive live simulation updates |

## 5. Python model architecture

| Area | Main files | Responsibility |
| --- | --- | --- |
| Thermodynamics | `thermo.py`, `tabulated.py`, `thermo_types.py` | Hydrogen state properties and fast tabulated runtime lookup |
| Hydraulic primitives | `components.py`, `pipes.py`, `network.py` | Restrictions, valves, relief devices, pipes, hose line-pack |
| Fueling equipment | `dispenser.py`, `protocol.py` | PCV/nozzle behavior, precooling, APRR/J2601-compatible schedule boundary |
| Vehicle | `vehicle.py` | Type IV gas, HDPE liner, and CFRP tank thermal model |
| Station | `full_station.py`, `scenario.py` | Cascade banks, compressor, sequencing, recharge, reference scenarios |
| Safe operation | `safe_operation.py`, `safety.py`, `safety_runtime.py` | Faults, latched safety PLC, ESD, leaks, HyRAM bridge |
| API and validation | `api.py`, `validation.py` | Job API, UI channels, H2FillS-compatible metrics |

### Main implemented physical scope

- Hydrogen storage mass, energy, and wall-temperature dynamics
- Three-bank cascade storage and break-before-make bank sequencing
- Three-stage compressor with intercooling and electrical power estimate
- Finite-UA precooler and finite-volume hose line-pack
- Real-gas choked/unchoked restrictions, check valve, PCV, nozzle, and relief primitives
- Three-zone Type IV vehicle tank model
- APRR pressure-ramp control and density/SOC completion condition
- Two H70 dispensing points sharing the station storage and compressor
- Sensor, actuator, cooling, compressor, ESD, and leak fault paths
- Leak mass/enthalpy removal from the process inventory
- Dynamic HyRAM+ consequence request bridge

### Property-model decision

CoolProp was used as the physical-property source for table generation, but the runtime is designed to use the hydrogen property table in `tabulated.py` instead of repeatedly calling CoolProp during simulation. This change was made to improve calculation speed for interactive operation.

The optional `table-build` dependency in `pyproject.toml` is the place to use CoolProp when regenerating or extending the table.

## 6. Safety and HyRAM status

- The safety runtime has independent latched safety logic; it is not merely a UI alarm.
- HyRAM+ 6.1 is optional. When installed, the native bridge is selected automatically.
- Default outdoor consequence observation points are 1 m, 3 m, and 5 m downstream at 1.5 m height.
- Indoor accumulation is not guessed. It requires `H2STATION_HYRAM_INDOOR_JSON` with an explicit enclosure definition.
- A deployment-specific evaluator can be selected with `H2STATION_HYRAM_EVALUATOR=module:function`.
- HyRAM+ 6.1 requires SciPy `>=1.11,<1.16`; this is pinned in `pyproject.toml` because of the HyRAM jet-solver callback compatibility constraint.

Important: HyRAM consequence calculation and annual QRA are intentionally separate. Do not report a live dynamic consequence result as an annual risk result.

## 7. Web UI and 3D operational view

The monitoring UI combines job progress, process values, safety state, risk state, and a Three.js-based 3D station view.

### Recent 3D work

- Detailed H70 station equipment, tube trailer, compressor skid, cooling package, storage banks, vent package, vehicle and hose routing
- Dual-dispenser visual and data channels
- Vehicle tank cutaway and corrected filling-port/hose placement
- Camera wheel zoom adjustments and automatic transparency for objects that obstruct the selected facility
- Green-field site context: varied surrounding buildings, trees, roads, sidewalks, service roads, parking, bus shelter, lights, and street furniture
- Front approach intentionally kept open so the station and fueling canopy are not blocked
- External pedestrians only: sidewalks, bus stop, side connectors, and rear research/office district
- Detailed parked sedans, SUVs, and vans; intermittent traffic on main and service roads

The surrounding buildings, people, parking cars, and road traffic are visual-only assets. They are not inputs to the process simulation, separation-distance logic, pedestrian exposure model, traffic safety model, or HyRAM calculation.

### Important 3D caution

The 3D additions documented in `docs/38` through `docs/45` were made iteratively in response to visual feedback. The latest exterior people and vehicle changes were not browser-revalidated after the final edit. Start the service and inspect the 3D tab before demonstrating or releasing the current branch.

## 8. Documentation map

The `docs` directory is deliberately chronological. Key starting points are:

| Document | Why it matters |
| --- | --- |
| `00_PROGRESS.md` | Early overall progress and project intent |
| `01_LITERATURE_AND_DATA.md` | Literature and data-source basis |
| `02_MODELING_BASIS.md` | First-principles modeling assumptions |
| `03_SAFETY_BASIS.md` | Safety approach and boundaries |
| `10_DYNAMIC_SAFETY_AND_HYRAM_RUNTIME.md` | Dynamic risk and HyRAM interface design |
| `12_API_AND_MONITORING_UI.md` | API and UI architecture |
| `13_HYDROGEN_PROPERTY_TABLE.md` | Runtime property-table decision |
| `38_DUAL_DISPENSER_PHYSICS.md` | Second dispenser physical integration |
| `40_3D_SITE_CONTEXT_AND_OCCLUSION.md` | Automatic visual occlusion/transparency |
| `43_3D_FRONT_CLEAR_ZONE_AND_BACKGROUND_DISTRICT.md` | Front-view protection and background district placement |
| `44_3D_ROADS_ACCESS_AND_PUBLIC_REALM.md` | Roads, entry/exit, sidewalks, and public realm |
| `45_3D_PUBLIC_ACTIVITY_AND_VEHICLE_DETAIL.md` | Latest people, parked vehicles, and road traffic work |
| `99_COMPLETION_STATUS.md` | Prototype completion statement and required validation evidence |

## 9. Current limitations and open checks

These points are important for the next account holder:

1. The model is feature-complete as a prototype, but calibration, manufacturer parameter provenance, and independent experimental validation remain outstanding.
2. SAE J2601 tables are licensed external inputs. The implementation uses a compatible schedule boundary and must not be presented as a licensed protocol reproduction without the appropriate input/license.
3. Verify the latest browser scene after transfer, especially the exterior traffic and detailed vehicle geometry added last.
4. The second dispenser is connected through the main safe-operation/API path. Before relying on the lower-level `FullStationModel.simulate()` path directly, re-check the secondary-dispenser command/state-vector path with a focused test.
5. HyRAM needs a compatible installation and appropriate licensing. Without it, use the configured fallback/external evaluator behavior and show that status clearly in the UI.
6. The visual site context is intentionally decoupled from physics and risk exposure. Do not infer site safety distances from its geometry.
7. Do not make engineering or operational decisions from the reference scenario until component parameters are fitted to traceable station and vehicle data.

## 10. Recommended next work, in priority order

1. Launch the transferred project and visually inspect the 3D tab; resolve any JavaScript/browser issues first.
2. Add a focused regression test for the two-dispenser path, including the direct `FullStationModel` API if it is to be supported.
3. Establish a parameter registry with units, data source, fitting bounds, uncertainty, and calibration status.
4. Compare the property table with its CoolProp source over the intended pressure/temperature envelope.
5. Validate component and partial-station trajectories against H2FillS and/or instrumented filling data.
6. Benchmark the HyRAM bridge against a documented native HyRAM+ case.
7. Decide whether visual site geometry should later drive detector placement, pedestrian exposure, or safety-zone overlays; these are not currently linked.

## 11. Transfer checklist

- [ ] Copy the project source tree to the new account/machine.
- [ ] Recreate `.venv` and install `.[api]`.
- [ ] Install `.[all]` only if HyRAM licensing and the intended use allow it.
- [ ] Start `.venv\Scripts\h2station` and open `http://127.0.0.1:8000`.
- [ ] Run or inspect the existing tests before making scientific claims about the model.
- [ ] Open the 3D operational view and confirm the latest scene loads correctly.
- [ ] Read `docs/99_COMPLETION_STATUS.md` before treating the package as validated.
- [ ] Keep future material changes recorded in a new numbered Markdown file under `docs`.

## 12. Working convention used so far

- Physics model changes are recorded in numbered Markdown documents under `docs`.
- Interface units are user-friendly at the API boundary: MPa, degrees Celsius, g/s, and mm; internal calculations are SI.
- New model parameters should be exposed as explicit fitting parameters rather than hard-coded hidden constants where feasible.
- Prefer first-principles relations and literature-backed assumptions over purely data-driven behavior.
- Keep HyRAM integration explicit and preserve the distinction between source-term physics and consequence-model assumptions.
