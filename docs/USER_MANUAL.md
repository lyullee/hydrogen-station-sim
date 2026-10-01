# Hydrogen Station Digital Twin — User Manual

## 1. Start and screen layout

Install Python 3.10+ dependencies with `pip install -e ".[api]"`, then run `h2station` (or `python -m h2station`). Open `http://127.0.0.1:8000` for the monitor and `/remote.html` for the controller. A SAGA service on port 8090 is needed for LLM answers; the process simulation and basic HAZOP display remain separate. The remote and monitor should address the same twin server/job. Use one server worker for a single in-memory job state.

The monitor has overview, process flow, equipment, CCTV, alarms, trends, sensors and SAGA views. The 3D scene can show the station, equipment details, CCTV/detector locations, live-photo reference, incident effects, consequence distance and risk floor overlay. The remote groups **operating settings**, **process control**, **incident injection** and **safety response**. The Korean/English selector is in the header; it persists across twin pages. For an English SAGA answer, choose English before sending a new request.

## 2. Prepare a clean run

1. Open **운전 설정 / Operating settings** on the remote.
2. Set each low, medium and high bank initial inventory as a percentage of its configured maximum pressure. The interface shows the resulting starting pressure. Specify trailer initial pressure/inventory and vehicle settings if needed.
3. Set each process target pressure and its **automatic stop** switch. When checked, the requested operation stops at its target. When unchecked, the normal target no longer stops the request; relief and independent protective trips can still intervene. Use this only as a virtual overpressure scenario.
4. Review relief valve enable switches and opening/reclosing pressures. Setting them close together is a chattering experiment.
5. Start monitoring. With no process command and no injected fault, the plant should stay idle and normal; minor virtual-sensor noise or model transients must not be read as physical alarms.
6. Use **계산 정지 · 완전 초기화 / Stop and fully reset** for a clean baseline. This stops the job and clears its simulated scene. A normal stop alone preserves more of the last displayed state.

## 3. Operate the process

In **공정 조작 / Process control**, start or stop the trailer-to-bank transfer path and vehicle 1/2 fills. The current remote links trailer supply and pressure recharge as one path; starting or stopping either card changes both requests. The vehicle fills remain independent. Check the active-path indicator on the 3D and process flow views; a requested process can still have zero flow when a valve is shut, source pressure is insufficient, a stop target is met, or safety protection has tripped. The hose should connect to the corresponding car only during its fill.

Select 0.5×, 1×, 2×, 3×, 5×, 10×, 30×, 50× or 100× target speed. Higher selection accelerates simulated time only as far as computation allows. Use **추세 / Trends** to compare pressure, temperature and flow on one time axis. Select storage, supply/compressor, fueling or all equipment; optional shading identifies incident-effect intervals. Vehicle 1 and 2 have distinct channels. If a value seems unchanged, inspect actual flow, ESD, isolation, auto-stop and the time scale before concluding a model defect.

## 4. Inject and inspect a scenario

Use **사고 주입 / Incident injection** to choose location, type, aperture/intensity and start time. Gas and flame detector indications, alarms, relief actions, inventory and pressure then respond according to the virtual model. Distinguish **injected incident**, **sensor indication**, **HAZOP candidate**, and **confirmed response**. A gas detector value is a modeled reading, not field evidence. The sensor workbench defaults to issue-only filtering; switch it off to inspect all sensors. Selecting a sensor opens its current value, related rules and stepwise response beside a separate LLM analysis. The analysis can be refreshed manually and follow-up questions go to the sensor channel.

The main SAGA panel is the general station conversation. **정기 분석 / Periodic analysis** can be turned off; user questions should still be sent manually. The main and selected-sensor conversations have independent endpoints. A warning/critical state may add calculated consequence context. Normal operation should not show accident impact as if a release occurred. Press **위험거리 / Impact distance** to display modeled distances in 3D; read the numeric criterion and calculation status too. The overlay is a scene aid, not an evacuation boundary. The **위험도 / Risk** floor overlay can show relative station ranking or a fixed 0–100 model index, configured on the remote with refresh interval. The absolute index is not annual fatality risk.

## 5. Perform virtual emergency response

The **안전 대응 / Safety response** tab is a training console. After confirming a scenario, use the staged panel: situation check → immediate action → stabilization → pre-restart inspection. A step may show a suggested executable action such as stopping recharge, isolating a bank inlet/outlet, stopping one dispenser, initiating ESD, venting or evacuating a zone. Click an action only after reading its target and the modeled effect. A **command** is not a confirmed valve closure: watch movement feedback and downstream flow. Injected device faults can make the command fail, leave internal leakage or provide false feedback. If the expected change does not occur, use the alternate isolation/escalation step. Isolation may leave pressurized hydrogen trapped; venting adds a discharge hazard. Ventilation, cooling, ignition/power control and evacuation are modeled separately.

Use the replay/compare view to review event time, command delay, success conditions and outcome differences. Recovery requires the modeled repair, tightness/detector/valve checks, purge, staged repressurization and approval sequence; a cleared alarm alone is not restart approval. The virtual exercise never controls real equipment.

## 6. Troubleshooting

| Symptom | Check |
|---|---|
| Process button appears ineffective | Job running, ESD, operation request state, source/target pressure, valve/isolation feedback, auto-stop setting and flow sensor. |
| Alarm immediately after start | Initial fill versus rule/relief limits, stale job not reset, virtual fault still active, sensor quality/origin. |
| Pressure does not fall during leak | Leak location and aperture, actual mass flow, bank recharge simultaneously adding mass, isolation/relief paths and selected trend channel. |
| LLM only reports status | Ask a direct question in the correct main or sensor channel; confirm SAGA health, selected provider key and that a streaming response completed. |
| No impact result | Verify an active incident/alert, HyRAM installation and per-scenario calculation status; normal-state omission is intentional. |
| 3D seems stale | Confirm current job and stream connection; refresh the browser only after recording the job ID. |

## 7. Language, data, and export

Use the top-right **한국어 / English** selector. The control labels switch immediately and the twin passes the language to new assistant requests. Historical messages, technical tags, measurements, regulatory source titles and some original Korean HAZOP material are not retroactively rewritten. English text is an aid for training; where exact regulatory wording matters, follow the cited Korean original. Export trends as CSV where offered and record initial settings, faults, time and safety actions for reproducibility. Do not put API keys or confidential site data in browser questions or screenshots.

For model internals, endpoints, assumptions and limitations, see [Technical Report](TECHNICAL_REPORT.md). For detailed staged virtual safety behavior, see [Virtual Safety Simulation](virtual-safety-simulation.md).
