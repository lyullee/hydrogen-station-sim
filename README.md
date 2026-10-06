# Hydrogen Station Dynamic Simulator

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23084421.svg)](https://doi.org/10.5281/zenodo.23084421)

The badge DOI resolves to the latest archived release. Earlier versions retain their own DOIs.

Original project software and associated documentation are available under the [MIT license](LICENSE). Bundled third-party libraries and assets retain their respective notices and terms.

## Current documentation

- [Technical report](docs/TECHNICAL_REPORT.md): architecture, physical model, safety logic, APIs, LLM boundaries, validation and limits.
- [User manual](docs/USER_MANUAL.md): startup, remote operation, incident exercises, response controls, trends and troubleshooting.
- [Paper evaluation](docs/PAPER_EVALUATION.md): repeatable fueling-boundary metrics and alarm-only versus SAGA-PY A/B scoring.
- [Public-data validation](docs/PUBLIC_VALIDATION.md): checksum-verified SAE J2601 experiments, HIAD incidents, dispersion data, and the publication-readiness gate.
- [Detector-logic replay](research/DISPERSION_DETECTOR_LOGIC_VALIDATION.md): a bounded 22-case replay of alarm/trip thresholds and persistence against public USN/FFI concentration measurements.
- [HyRAM adapter verification](docs/HYRAM_ADAPTER_VERIFICATION.md): exact v6.1 source identity, upstream experimental validation-suite execution, and field-by-field production-adapter parity.
- [Consequence geometry validation](research/CONSEQUENCE_GEOMETRY_VALIDATION.md): bounded public-experiment-to-browser traceability for directional plume and sampled radial effects.
- [PRESLHY blowdown validation](research/PRESLHY_BLOWDOWN_EXTERNAL_VALIDATION.md): prospectively specified 22-case external result, including retained negative cases and claim boundary.
- [PRESLHY non-adiabatic development](research/PRESLHY_NONADIABATIC_DEVELOPMENT_RESULT.md): immutable follow-up on consumed cases; 20/22 pass the original diagnostic screens but cannot serve as external confirmation.
- [PRESLHY E5.1 holdout protocol](research/PRESLHY_E5_1_HOLDOUT_PROTOCOL.md): model-hash-locked independent evaluation rules frozen before archive access.
- [PRESLHY E5.1 holdout result](research/PRESLHY_E5_1_HOLDOUT_RESULT.md): retained ineligible negative result; 3 primary ambient cases and 2/3 joint passes did not meet the frozen minimums or 70% rule.
- [Independent 90 MPa release holdout](research/PROUST_RELEASE_HOLDOUT_RESULT.md): prospectively frozen INERIS/CEA mass-flow transfer test; all three nozzle series were eligible and all failed the joint screens.
- [HIAD expert-review protocol](docs/EXPERT_REVIEW_PROTOCOL.md): frozen casebook, masking, reviewer rubric, endpoints, and analysis plan.
- [HIAD evaluation readiness](research/hiad_evaluation_readiness.json): machine-checkable status of coordinator review, ethics, holdout collection and independent expert-review gates; advisory prescreen output never counts as approval.
- [IJHE working manuscript](manuscript/ijhe_manuscript_draft.tex): claim-bounded English draft, journal-format checks, figures, graphical abstract and the remaining submission gates.

The monitor and remote now have a Korean/English language selector. New main and sensor assistant requests use the selected output language while consequence calculations and source data remain unchanged. English answers are advisory translations/analyses; verify exact safety requirements against their original source.

Physics-first Python simulator for gaseous hydrogen refueling stations. The existing
Java/browser simulator is a visual reference only; this package has an independent
model, API, and monitoring interface.

## Implemented system

- CoolProp-generated hydrogen property table (runtime lookup; no CoolProp calls in the process solver)
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

The process solver reads `src/h2station/data/hydrogen_properties_v1.npz`, generated
offline by `scripts/generate_hydrogen_table.py`. PCV/nozzle/release choking uses a
small critical-pressure lookup derived from that same table; unusual pressures or
temperatures outside its operating grid fall back to direct table-based search.

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

## Monitoring and sensor provenance

The monitor keeps the 3D station footprint, process flow, equipment specifications,
and CCTV gallery in the same 16:9 display region. The 3D scene omits the surrounding
district and traffic, and caps render resolution to reduce GPU load. The equipment
and CCTV top-menu entries switch that region without opening a separate dialog.

API monitoring jobs enable simulation outputs for all 82 HAZOP database sensor tags.
The 15 gas detector tags are virtual zone proxies that respond to injected leaks or explicit sensor faults;
they are not physical detector connections. Compressor-stage readings follow the
three-stage model. Shared header and precooler channels are derived from upstream
flows and temperatures. The coolant flow channel is a thermal-equivalent estimate;
the vent channels use an assumed ambient boundary until a release is injected.
Each API signal includes an `origin`, while `/api/hazop/mapping` reports its binding
and still reports zero physical sensor connections. Site telemetry should replace
these proxies before operational use.

## Operator process control

The remote's **안전 대응** tab adds simulation-only equipment isolation, delayed
valve position/flow confirmation, venting, ventilation, cooling, evacuation,
recovery tests, and training replay. Active sensor scenarios and SAGA response
cards provide the same executable virtual actions. See
[`docs/virtual-safety-simulation.md`](docs/virtual-safety-simulation.md) for the
model assumptions, recovery gates, and limits.

Open `/remote.html` and start continuous monitoring. The trailer supply, storage-bank
recharge, and each of the two vehicle fills begin **off**. The process inventories
remain unchanged while no command or fault is active. The remote couples trailer
supply and storage-bank recharge on one transfer path; either start/stop control
changes both requests. Vehicle 1 and 2 fills remain individually controlled and
draw from the cascade banks.

The remote offers 0.5×, 1×, 2×, 3×, 5×, 10×, 30×, 50×, and 100× target speeds and
allows switching during a run. This changes wall-clock pacing without enlarging
the physical solver step. The remote shows both the selected target and measured
speed; a computation-bound run may stay below its target. Accident delays entered
during a run are anchored at the solver step that accepts the command.

The remote exposes a finite trailer inventory, initial pressure and temperature,
individual bank starting fills, and configurable bank/vehicle stopping pressures.
Each process target has an automatic-stop switch. Turning it off allows a virtual
overfill exercise; relief valves and independent ESD protections remain separate.
Trailer pressure falls as compressor transfer removes mass. Its fixed volume and
isothermal temperature are explicit reference-model assumptions.

Seven virtual relief valves cover the three storage banks, two dispenser hoses,
and two vehicle tanks. Their enable switches, opening and closing pressures, and
orifice sizes are adjustable during a run. A valve stays open until pressure
falls to its closing setting; close opening/closing settings reproduce sampled
chatter. Relief mass flow is deducted from the corresponding inventory and enters
the same leak, detector, HAZOP, and consequence pipeline as other releases. These
settings are simulation inputs, not certified relief-valve sizing values.

The remote shows command acknowledgement separately from actual flow, including
why a requested path is waiting or blocked. It also displays wall-clock lag and
simulation speed. Operator-mode integration uses SciPy LSODA, while the legacy
batch API retains BDF. Continuous operator monitoring paces successful solves to
wall time; if a step takes longer than real time, the solver keeps all physical
steps and reports the accumulated lag instead of silently skipping them.

## HyRAM configuration

When `hyram==6.1` is installed, the native adapter is selected automatically. Default
outdoor observation points are spaced every 0.5 m from 0.5–10 m, then at
12, 15, 20, 25, 30, 40, and 50 m downstream at 1.5 m elevation. The reported
extent is the farthest threshold-exceeding sample, not a certified safety radius.
Override them with JSON:

```powershell
$env:H2STATION_HYRAM_LOCATIONS='[[0.5,0,1.5],[1,0,1.5],[1.5,0,1.5],[2,0,1.5],[2.5,0,1.5],[3,0,1.5],[5,0,1.5],[10,0,1.5]]'
```

Site overrides replace the entire default sampling transect. Sparse overrides
can make a threshold crossed between two points appear at the nearer point.

Indoor accumulation requires an explicit enclosure definition through
`H2STATION_HYRAM_INDOOR_JSON`; no enclosure geometry is invented. A site-specific
backend can instead be selected with
`H2STATION_HYRAM_EVALUATOR=module:function`.

The digital-twin SAGA panel and selected-sensor follow-up questions use dedicated
`/direct` API routes. The simulator first evaluates the current sensor state,
then sends the operator's actual question and its calculated context to SAGA's
single-completion LLM endpoint. This bypasses SAGA's multi-stage RAG/review
pipeline but retains free-form question answering. The operator can manually
select Service Hub or Groq. Groq's direct model defaults to Qwen with reasoning
disabled; Service Hub defaults to the non-reasoning Llama instruct model. If the selected LLM is
unavailable, the interface labels the connection error and retains a local
sensor-based fallback answer. The older analysis API remains available for
existing integrations, but the digital-twin interface does not call it.

Consequence evaluation remains in the direct path. An active warning/critical
state automatically evaluates relevant nodes before building the answer. Normal
operation only evaluates consequences when the operator explicitly requests an
impact or uses **센서 기준 가상 평가**. The calculations use current GOOD-quality
pressure and temperature readings. An active leak uses its current orifice size
and flow; a hypothetical case uses a 1 mm horizontal release at 1 m height and
101325 Pa ambient pressure. The calculated result, sensor tags, and assumptions
are passed to both the direct state endpoint and the one-pass LLM. Reported distance is the farthest sampled
point exceeding 5 kW/m² or 5 kPa, not a validated site safety boundary. Missing
sensor pairs or an unavailable backend never produce an invented distance.

## Engineering status

This is a modeling and monitoring prototype, not a certified controller. Reference
scenario dimensions and thermal parameters are illustrative until calibrated against
traceable equipment and test data. SAE J2601 tables remain licensed external inputs.
The complete modeling basis, literature, limitations, and validation plan are in
`docs/`.

The partial-station boundary experiment is documented in
[`docs/PARTIAL_STATION_VALIDATION.md`](docs/PARTIAL_STATION_VALIDATION.md).
It is a development diagnostic with an explicit upstream-pressure assumption;
it does not upgrade the full-station validation claim.

The current public-data intake lead is documented in
[`research/NBSDC_HEAVY_VEHICLE_FAST_REFUELING_ACCESS_RECHECK_2026_10_06.md`](research/NBSDC_HEAVY_VEHICLE_FAST_REFUELING_ACCESS_RECHECK_2026_10_06.md).
Its numerical files require an approved portal request. Once a rights-cleared
workbook is obtained, the explicit-unit loader in
[`src/h2station/nbsdc_ingest.py`](src/h2station/nbsdc_ingest.py) can produce
in-memory pressure, temperature and flow traces without publishing raw rows.
The test-cylinder data remains a component/protocol candidate until its mapping
to a vehicle-side validation contract is independently confirmed.
