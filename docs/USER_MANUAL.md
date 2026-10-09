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

For a hydrogen leak, select its **release-source boundary** explicitly. **Free orifice** calculates flow from source pressure, temperature and aperture. **Flow-limited line/process** applies the lower of that free-orifice result and the entered maximum release flow. Use the latter only when a defensible upstream line, regulator, compressor or dispenser limit is known. The setting and limit are retained in the live fault list and consequence evidence so runs can be reproduced. It is not an automatic calibration factor.

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

## 8. Guided exercises and expected evidence

### Exercise A — baseline and normal fueling

Start from **full reset**, leave all incident slots empty and keep the normal automatic-stop and relief settings on. Start monitoring without a process request: process flow should remain idle, no modeled release should be present and the incident panel should not invent a critical warning. Start **vehicle 2 fueling** only. Confirm the vehicle 2 hose connects in the 3D view, vehicle 1 remains disconnected, the vehicle 2 tank pressure/inventory change in its own trend and the selected bank inventory responds. Stop vehicle 2 manually or allow its selected target pressure to stop it; the hose should return to the dispenser. Save the trend and note the simulated time. A temporary nonzero command with zero actual flow is a diagnostic state, not proof of fueling.

### Exercise B — overfill target switch

Use full reset. Set a reachable bank/vehicle target and leave automatic stop **on** for a first run; note the stop time, final pressure, relief state and ESD. Reset and repeat with the normal target switch **off**. The process request should continue past the configured stop target unless another modeled constraint intervenes. Observe the separate relief opening/reclosing values and ESD. Record which protective layer actually stopped or vented the flow. Do not describe “auto stop off” as disabling all protection: that is intentionally not how this model works.

### Exercise C — storage leak, isolation and residual inventory

Full reset and inject a leak at a named bank. Start the run and use the **sensor workbench** to compare its pressure, temperature, flow and nearby gas detector readings; inspect the fault's origin and quality. In the main/SAGA view, read calculated consequence status, assumed leak diameter and observation criterion rather than treating the 3D extent as a certified evacuation distance. In **Safety response**, command upstream isolation; wait for movement and closure feedback, then verify downstream flow. A pressure decline after isolation may continue from gas already trapped in the bank or line. If the action fails, inspect stuck/seat-leak/feedback faults and use the escalation branch. Venting introduces a separate discharge path: compare its release indication with the original leak. Finish with stabilization and recovery tests; use full reset for a new baseline.

### Exercise D — fire, cooling and evacuation

Inject an external-fire scenario at a chosen equipment zone. Confirm the virtual flame detector's **detected/pending** state before describing a fire as sensed. Compare equipment temperature, bank pressure, relief activity and adjacent-zone effects over time. Activate cooling and relevant isolation/ESD, then track the temperature trend and relief status. Restrict access and evacuate the modeled people/vehicles by zone; compare available routes with wind direction. Mark each step complete only when its virtual success condition is met. Restart remains gated by repair, tightness, detector/valve tests, purge where relevant, staged pressure test and approval. The model does not replace a site fire brigade or actual emergency plan.

## 9. Interpreting signals and assistant output

| Display field | Interpretation |
|---|---|
| Tag/value/unit | Virtual instrument reading at a particular simulated time. Check `quality` and `origin`. |
| Alarm candidate versus active warning | A threshold may need persistence, state and other evidence; read its current status and history. |
| Model leak flow | Flow removed from a modeled inventory; compare with the corresponding pressure/mass trend. |
| Gas or flame detector | Simulation proxy responding to a modeled incident/fault; not an independent field measurement. |
| Consequence status | `calculated`, unavailable or insufficient input must be distinguished before quoting a distance. |
| Sampled effect distance | Furthest tested point crossing the chosen criterion, with next non-crossing point when available; not an approved exclusion radius. |
| Relative / absolute risk floor | Comparative model index only; does not express annual individual fatality risk. |
| Virtual action status | Commanded, moving, confirmed or failed. Validate flow and the next frame. |

The assistant is deliberately separate from process control. A question such as “close the high-bank inlet” may receive advice and a mapped **virtual action button**; text alone is not evidence that a valve moved. If the text conflicts with the sensor pane, trust the structured current readings and investigate the discrepancy. English output uses the same structured inputs and consequence results; tag names, units and original cited Korean safety material may remain untranslated for traceability.

## 10. Reading validation status in assistant answers

The assistant receives a compact `validation_readiness` summary from the same
committed evidence ledger used by the research report. At the current snapshot
the ledger is **125 PASS · 10 FAIL · 7 PENDING** and does not authorize a claim
of externally validated station-to-vehicle full-loop behavior. This status is
shown to keep answers grounded; it is not a live plant alarm and it does not
change the simulator state.

The claim guard is fail-closed. If the ledger is missing, malformed, or says
that full-loop evidence is unsupported, the answer must describe the result as
modelled, conditional, component-level, or station-side as appropriate. A
successful HyRAM calculation, a local station replay, or a populated HAZOP
response does not override the failed or pending gates. Use the committed
audit JSON and its linked reports for the evidence boundary, and use the
simulator UI only for the virtual operating exercise.

## 11. Run record checklist

For a useful training record, save the Git version, local date/time, job ID and simulation speed; starting bank percentages and vehicle/trailer state; process targets and stop switches; relief set points; fault type/target/aperture/timing; selected sensor quality and trend export; calculated consequence status and criteria; virtual action sequence with issue/feedback/flow timestamps; and the final recovery decision. Two runs can only be compared fairly when their initial and injected conditions match. The **Safety replay / compare** functions help identify the effect of response delay, wrong isolation and unverified closure.
