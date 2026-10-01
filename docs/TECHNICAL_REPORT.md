# Hydrogen Station Digital Twin — Technical Report

## 1. Scope and architecture

This repository implements a **simulation-oriented** gaseous H70 hydrogen-station digital twin. Its Python process model, virtual instruments, fault engine, consequence bridge, safety workflow, FastAPI service, and browser clients run independently of the SAGA knowledge service. It is not a certified control system, physical sensor connection, or site-specific quantitative risk assessment. The default service listens on port 8000; SAGA normally listens on 8090.

```text
Remote control / monitor / 3D scene
                │ HTTP + WebSocket
                ▼
       h2station.api (job lifecycle)
          ├─ process solver → virtual sensors → trend frames
          ├─ fault injection → safety PLC / relief / ESD
          ├─ HAZOP rules → staged response / virtual actions
          ├─ consequence coordinator → HyRAM+ adapter
          └─ main and sensor assistant clients → SAGA integration API
```

The browser has separate main-conversation and selected-sensor paths. Their requests go to distinct digital-twin API routes, which call the matching SAGA integration routes; the general SAGA RAG chat is a third path. See [LLM API boundaries](llm-api-boundaries.md).

## 2. Process representation

`src/h2station/full_station.py` integrates the trailer, compressor, cascade banks, precooling, hoses, two dispensers, and vehicle vessels. Components in `components.py`, `network.py`, `pipes.py`, `dispenser.py`, and `vehicle.py` retain mass and energy inventories. `tabulated.py` reads the bundled `hydrogen_properties_v1.npz` property grid, generated offline from CoolProp; the process solver does not call CoolProp on every step. `thermo.py` contains thermodynamic interfaces and conversion. Internal quantities use SI; API/UI boundaries use MPa, °C, g/s and mm where labelled.

Trailer supply and bank recharge share one transfer path in the current remote UI: starting/stopping either couples the two requests. Vehicle 1 and 2 filling are individually requested. Idle jobs do not silently perform those operations. User-configured stop targets can be enabled or disabled; disabling a normal target permits overfill demonstrations, while relief settings and independent trip logic remain separate. Three banks have distinct pressure limits and initial fill percentages. Pressure alone does not establish a unique stored mass without volume and temperature; the solver performs the conversion using its state and property table. `protocol.py` implements an APRR-style filling boundary and protective limits; it is a model of protocol behavior, not proof of full SAE J2601 certification.

`operations.py` handles process commands, `simulation_clock.py` target time scaling, and `safe_operation.py` the operating envelope. Selecting 0.5×–100× changes target wall-clock pacing, not physical time-step size; actual speed is bounded by CPU and consequence calculations. The recharge controller uses hysteresis to avoid rapid start/stop near its upper target. Check process settings and sensor trends before interpreting apparent plateaus.

## 3. Faults, detection, and protective systems

`scenario.py` defines injected leaks, fires, process failures and their timing. `safety.py`, `safety_runtime.py`, and `hazop/` evaluate virtual sensor signals and protective actions. Virtual detector values must be read with their `origin`/quality; they are not proof that real equipment detected an incident. Gas and flame indications are driven by the simulation/fault model. Alarm thresholds, persistence, latching, and reset behavior are separate from the incident input. Alarm candidates alone do not establish a confirmed release.

Configurable relief valves use opening and reclosing set points, allowing hysteresis/chattering experiments. ESD and isolation have state and feedback distinct from a command. `virtual_safety.py` models individual isolation valves, commanded movement, observed closure, flow confirmation, stuck/leaking/feedback failures, venting, ventilation, cooling, evacuation, recovery gates and action replay. These are virtual exercises: a click never actuates physical plant. An incident can continue in an isolated inventory until its modeled mass, heat and vent paths evolve; clearing a badge is not equivalent to physical verification.

The HAZOP catalog is bundled in `src/h2station/data/hazop.sqlite3`, with additional playbooks in `emergency_playbooks.json`. `hazop/mapping.py` maps rules to sensor tags; `hazop/engine.py` evaluates conditions; `hazop/response.py` and `scenario_actions.py` select staged safety measures. The UI groups correlated indications into a plausible joint scenario rather than treating each threshold as a separate accident. [Virtual safety model](virtual-safety-simulation.md) and [emergency response coverage](emergency-response-coverage.md) give the detailed action and recovery assumptions.

## 4. Consequences and risk presentation

`risk/coordinator.py`, `risk/runtime_backend.py`, `risk/hyram_adapter.py`, `risk/live.py`, `risk/sensor_assessment.py`, and `risk/scenario_planning.py` coordinate sampled releases, candidate hazards and consequence estimates. HyRAM+ 6.1 is an optional runtime dependency. Results depend strongly on assumed leak diameter, pressure, temperature, release orientation, enclosure and exposure criteria. A displayed minimum/rounded distance is a visualization/reporting result, **not** a safety setback. Compare the exact reported criterion and calculation status before using any radius. Normal operation should not create a fictitious release consequence solely to populate a card; alarm/incident analysis may calculate and pass consequences into the LLM context.

The 3D risk-distance display is a visual representation around equipment footprints. Relative risk compares current equipment within this virtual station; absolute display is a fixed 0–100 model index, **not annual individual risk or a validated QRA frequency**. Risk refresh intervals are adjustable to bound compute load. Historical trend shading identifies modeled incident-effect intervals and can be switched off.

## 5. APIs and state ownership

`src/h2station/api.py` owns simulation jobs in process memory. Principal routes:

| Purpose | Route family |
|---|---|
| Health/defaults | `/api/health`, `/api/config/defaults` |
| Job lifecycle | `POST /api/simulations`, status/result/frames/stream, stop |
| Process control | `.../operations`, `.../speed` |
| Fault injection | `.../faults` |
| Virtual response | `.../safety`, `.../safety/actions`, faults, environment, replay, compare |
| HAZOP | `/api/hazop/catalog`, mapping, emergency-responses, job HAZOP |
| Consequence/risk | `.../risk-zones` and analysis response payloads |
| Assistants | `.../assistants/main`, `.../assistants/sensors/{sensor_id}` and stream variants |
| Sensor workbench | `.../sensors/{sensor_id}`, `.../analyze` and stream/direct variants |

Inputs are Pydantic models and invalid jobs/actions return HTTP errors. WebSocket frame streaming and HTTP polling both consume the same job state. Jobs are ephemeral across server restarts. Do not run multiple app workers expecting a shared in-memory simulation; an external job store would be needed.

The main and sensor assistant requests accept `language: "ko" | "en"`. The selected language is passed to SAGA's **dedicated** integration APIs as `output_language`, without altering the process calculation or consequence inputs. General SAGA RAG chat and the two twin assistants must remain separate for reliable command handling.

## 6. Front-end and internationalization

`web/index.html` is the monitoring station, `web/remote.html` the process/incident controller. `web/station3d.js` and related 3D modules render equipment, cameras, detectors, accident effects and overlays. `web/saga-bridge.js` and `web/sensor-workbench.js` manage the two assistant channels. `web/locale.js` adds a Korean/English selector, persists the preference in browser storage, translates interface chrome as views are updated, and synchronizes tabs. It does not translate technical tags, measured values, source citations or user-authored questions. The original HAZOP catalog and some source guidance remain Korean; English assistant output is a presentation language, not a translated regulatory source.

## 7. Reproducibility and validation

Install with Python 3.10+ and `pip install -e ".[api,test]"`; include `[risk]` or `[all]` when HyRAM+ is needed. Run `h2station` or `python -m h2station`. Execute `python -m pytest -q` after an editable install, or set `PYTHONPATH=src` when running directly from checkout. The test suite covers process inventory, operations, alarms, detectors, HAZOP, virtual safety, concurrency, API and LLM integration boundaries. The bundled property table and HAZOP database are versioned model inputs. See [operating conditions review](operating-conditions-review.md) for empirical assumptions and [station visual scale](station-visual-scale.md) for scene dimensions.

For a repeatable exercise, record the Git commit, Python/dependency versions, job settings, initial bank fills, stop-target/relief settings, injected faults, time scale, weather/ventilation assumptions and HyRAM version. Save trends and the virtual action replay. A modelled response should be validated against actual plant drawings, detector coverage, relief discharge design and competent engineering review before operational interpretation.

## 8. Known boundaries

The model is a training and research simulator. All sensors are simulated; no actual PLC, CCTV or gas detector is connected. The 3D image and CCTV illustrations are representational. The station layout, volumes, heat transfer, compressor performance, leak geometry, population and meteorology are scenario assumptions, not an as-built survey. Weather-dependent dispersion, structural failure, detailed indoor CFD and full probabilistic risk are outside the model's validated scope. HyRAM outputs are conditional consequences, and a successful LLM response does not validate a safety decision. Operators must use actual site procedures and measurements for real incidents.
