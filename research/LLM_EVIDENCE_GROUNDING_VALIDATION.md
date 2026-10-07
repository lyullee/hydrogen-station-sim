# LLM evidence-grounding validation

**Recorded:** 2026-10-08
**Scope:** digital-twin main assistant and selected-sensor assistant routes

This record documents a software-level grounding check. It is not a human
expert-effectiveness study and does not establish that the assistant improves
operator decisions.

## Contract

Each assistant request now receives an `evidence_manifest` generated from the
same simulator frame used by the deterministic analysis path. The manifest
contains:

- simulation time and an explicit `DIGITAL_TWIN_SIMULATION` source marker;
- sensor tags, values, units and quality status (with a bounded prompt view and
  an omitted-row count);
- active condition labels and associated sensor tags;
- response evidence identifiers (for example HIAD, H2Tools and ISO mappings)
  included per condition and in an aggregate source list;
- public HIAD action-to-playbook traceability metadata with an explicit
  non-efficacy claim boundary;
- a compact HIAD action taxonomy (eight derived action categories, category
  counts and the action-evidence artifact digest) without raw incident prose;
- public KHK accident-report inventory metadata (23 linked reports, 26 incident
  codes and 8 precaution reports) with citation-only rights and no mirrored PDF
  text;
- a derived KHK scenario-precedent map linking all 23 report records to
  conservative response families with counts and representative citations;
- scenario-specific KHK precedents selected from the active response family and
  delivered consistently to the full evidence manifest, compact provider prompt
  and staged operator guidance;
- impact calculation state: `not_requested`, `attempted_no_result`, or
  `calculated`;
- calculated impact basis, input sensor tags, model outputs and threshold
  interpretation limits;
- the public Grune/Sempert measured ventilation envelope (42 profiles and
  42 no-wind-normalized factors) with a runtime scope limited to the virtual
  detector proxy. Active releases use the measured upper spatial envelope by
  default; the central median remains available for sensitivity runs;
- the detector alarm/trip policy loaded from the public concentration replay
  record (1.0 vol% H₂ alarm, 2.0 vol% H₂ trip, 0.5 s persistence) together
  with its DOI and explicit outdoor-dispersion/ESD claim boundary;
- the public concentration-scale coefficient used by the virtual detector
  proxy (22 cases, median final-third sensor-grid P90 concentration divided by
  measured mean release flow), together with its DOI, formula and explicit
  open-channel-only claim boundary;
- an opt-in, de-identified station-boundary pressure scope diagnostic in each
  operator frame and evidence envelope. It reports whether the simulated
  source pressure is inside the observed range, without turning that range
  into a safety limit, trip criterion, or full-loop validation claim;
- a privacy-bounded private-media intake boundary. Screen recordings and
  equipment photos are exposed only as provenance/inventory status; they are
  explicitly marked as non-machine-readable and cannot authorize parameter fit
  or a full-loop claim;
- public real-station operating context for back-to-back fueling, with its
  synchronized-raw-log and full-loop eligibility boundary;
- the five-session MetHyTrucks HySaM no-fit tank diagnostic, including the
  244 L candidate replay, 77 L geometry sensitivity and the unresolved public
  workbook-to-sink crosswalk;
- cross-campaign public release-validation outcomes kept at campaign level:
  one supported transient, two failed eligible campaigns and one ineligible
  pressure-decay candidate, with no universal release-model claim;
- public operating-range benchmarks for 35 MPa transportable supply and H70 high-flow filling, with pressure-class selection and an explicit partial-boundary/full-loop claim limit;
- consequence flow-boundary status, requested process flow, HyRAM modeled flow,
  and an explicit mismatch claim limit when high-pressure choked flow causes
  the physics adapter to recompute the release rate;
- a SHA-256 digest over the canonical manifest contents.

The manifest explicitly states that simulated signals are not field
measurements and that sampled consequence distances are not confirmed safety
distances. An LLM response is not allowed to turn `not_requested` or
`attempted_no_result` into a calculated impact result.

## Checks executed

The following tests passed in the repository virtual environment:

```text
.venv\Scripts\python.exe -m pytest tests/test_llm_grounding.py tests/test_public_tank_calibration.py tests/test_digital_twin_direct_qa.py tests/test_hiad_action_playbook_coverage.py tests/test_hiad_accident_response_coverage_evaluation.py -q
31 passed, 2 warnings

.venv\Scripts\python.exe -m pytest -q
811 passed, 14 warnings
```

The tests verify that normal monitoring keeps impact calculation marked as
`not_requested`, emergency or explicit-impact paths preserve calculated
results and input tags, non-finite values are discarded, the main and sensor
assistant routes remain isolated, and a generated answer cannot negate a
confirmed alarm, gas observation, physical leak or calculated impact.
The manifest digest now also covers the public response-source identifiers, the
HIAD action-to-playbook traceability metadata, the derived HIAD action-category
counts and their artifact digest, and the KHK citation inventory used to ground
the staged action plan. Raw HIAD action prose is never inserted into the live
prompt.

The accidental-release evidence envelope links the open Zenodo archive and
its parent article to qualitative release/ignition scenario grounding. It exposes
only compact channel, row-count, time-range and local-hash metadata; the raw
workbooks are never copied into the prompt, and the record remains ineligible
for a station-to-vehicle full-loop holdout or ignition-probability claim.

The consequence handoff also records whether a supplied process-flow boundary
was retained.  If HyRAM's high-pressure choked-flow path recomputes a different
release rate, the status and ratio are carried into the impact record and LLM
evidence envelope; the result is explicitly limited to model-bound screening.

The evidence envelope now also carries the public MetHyTrucks/NPL sampling
workbook context: two CC BY records, 13 files and an observed 0.5 s sampling
interval. The public metadata do not identify vehicle/receptacle channels, so
this remains instrumentation context rather than a station-to-vehicle
validation result.

The MetHyTrucks HySaM numerical diagnostic is now carried separately from that
instrumentation context. Five measurement-only selected sessions from two
workbooks are exposed as a no-fit component diagnostic. With the 244 L candidate
sink, the case-mean pressure and temperature RMSE are 1.287 MPa and 4.578 °C;
all five pass the project's descriptive screen. The same sessions evaluated at
77 L yield 13.131 MPa and 18.948 °C, with one descriptive pass. The public
supplement still provides neither a logger-channel dictionary nor a
workbook-to-244/77 L setup crosswalk. Every assistant projection therefore
receives both the measured result and `claim_supported=false`,
`prospective_holdout_eligible=false`, and
`full_loop_validation_eligible=false`. The five sessions are not described as
five independent events because sessions within a workbook may be correlated.

PRESLHY development and independent holdout outcomes are carried separately.
The development set passes 20 of 22 cases, while the independent E5.1 ambient
holdout passes 2 of 3 cases and does not meet its minimum-case or claim
threshold. The runtime release parameters remain unchanged, and the LLM is
shown this boundary explicitly.

The release-model evidence is also projected across four public campaigns
without averaging away disagreement. Ekoto 2012 passes its frozen transient
mass-flow screen (NRMSE 3.845%, median APE 12.791%, half-time error 6.068%).
Schefer 2006 fails the joint mass-flow screen despite a 5.832% NRMSE because
median APE is 22.852% and half-time error is 28.295%. Schefer 2007 fails the
pressure-decay screen (NRMSE 11.581%, median APE 27.464%), while Grune 2014 is
ineligible because the accessible record cannot support a trace-specific
measured half-pressure time. Thus the assistant receives one supported, two
failed and one ineligible result. The apparatus-resolved valve/line-pack
protocol remains unexecuted, no production parameter was changed after seeing
these outcomes, and no universal release, station, consequence-distance or
field-safety validation claim is permitted.

The privacy-bounded station-equipment envelope is also carried with its
pressure range, temperature range and state-transition count. Temperature and
state semantics remain unattested, and the artifact contains no vehicle-side
channels or full-loop validation claim.

The private pressure bundle is additionally summarized by generic channel
index. The two measured boundary channels show materially different pressure
envelopes (median values of 43.2896 and 82.8211 MPa in the bounded sample), so
the assistant can distinguish a channel-specific operating context instead of
pretending that one station-wide pressure value represents every bank. The
channel-to-bank identity is intentionally not published or inferred, and the
summary is therefore evidence-only: it is not automatically applied to
controller parameters.

The owner-attested lifecycle-counter summary is carried separately. Its
full-bank pressure units are available for operator/LLM history context, while
the absence of a validated degradation relationship keeps capacity, leak-rate,
relief-setting and failure-probability changes out of the physical model.

The public real-station back-to-back fueling record is carried as a source
link and scenario context. It is not treated as a raw synchronized holdout
because the public record does not provide reusable event-level logger rows.

The Grune/Sempert envelope is a measured-boundary adjustment for the virtual
detector proxy. It uses the public DOI and aggregate factors only, defaults to
the measured upper spatial envelope during an active release, falls back to a
neutral factor for unrepresented conditions, and does not modify the physical
release model, HyRAM consequence result, controller parameters or full-loop
validation status.

The detector persistence rule is now applied through the same public replay
record instead of remaining an unexplained pair of constants in scenario
assembly. This is a logic/provenance change only: the concentration proxy,
detector placement, outdoor dispersion and ESD effectiveness are still outside
the record's claim boundary.

The concentration proxy scale is now derived from the same public traces rather
than an arbitrary `mass_flow × 10000` factor. The recorded median coefficient
is applied before the measured ventilation/wind envelope and is bounded at
100 vol% H₂. This reduces instant saturation for small leaks while retaining a
clear advisory boundary: the open-ended channel data do not validate an
outdoor station plume, detector placement, ESD effectiveness, or consequence
distance.

The frozen station-to-vehicle external holdout is also carried as a hard claim
boundary. Eight public MC-default cases were evaluated under a protocol frozen
before data access; the pressure, temperature and final-SOC screens passed 0/8
(mean RMSE 15.862 MPa, 13.230 °C and 18.082 percentage points). Five cases
stopped at the gas-temperature safety limit. A later parameter sweep reduced
aggregate error but still passed 0/8; it is explicitly marked post-freeze
diagnostic-only and cannot be used as validation, certification or a production
parameter-fitting result.

The public NREL H2FillS HDVS Type-IV tank screen is now carried as a separate
partial-boundary record. Seven tanks and 351 samples are evaluated with measured
mass-flow, inlet-temperature and pressure boundaries; pressure RMSE is 6.164
MPa, temperature RMSE is 4.625 °C, and the predeclared joint screen passes 0/7.
The EOS-equivalent volume ratio (median 0.911 relative to the frozen effective
volume) is retained as a geometry diagnostic only. It is not applied as a
production correction, and it cannot support a station-controller, receptacle or
full-loop accuracy claim.

The same public workbook is also exposed as a post-access geometry-sensitivity
diagnostic. A capacity/EOS volume basis screens 7/7 tanks in both the frozen-fit
and no-volume-fit variants (mean pressure RMSE 3.538 and 0.496 MPa; mean
temperature RMSE 4.255 and 4.185 °C). Because the workbook was available before
the comparison, these results are not an independent confirmation. The runtime
therefore keeps `reference` as the default, exposes `capacity_eos` only as an
explicit opt-in, and tells the assistant that a frozen prospective holdout is
still required.

The evidence envelope also carries the public HyTF 70 MPa tank trace as a
component-boundary candidate: 2,536 synchronized samples, two pressure
channels and fourteen thermocouples. The source commit and hash are preserved,
but the absence of mass-flow, vehicle/receptacle and controller/ESD channels
keeps `claim_supported=false` and prevents any full-loop interpretation.

Every simulation snapshot now carries its selected vehicle geometry basis and
declared capacities into the hashed evidence envelope. This prevents the main
and sensor assistants from describing an opt-in capacity/EOS sensitivity run
as if it were the reference-default run.

## Claim boundary

This is traceability and consistency evidence for the software contract. It
does not validate the underlying hydrogen physics, establish field safety, or
measure SAGA's usefulness, omission rate, unsafe-advice rate, latency, or
operator performance. Those require an independently frozen casebook and
qualified expert review, which remain pending in
`manuscript/ijhe_readiness_audit.json`.


## Public incident traceability follow-up

The reproducible [HIAD-to-playbook coverage audit](HIAD_ACTION_PLAYBOOK_COVERAGE.md)
links 34 public HRS incident/near-miss metadata rows to the current emergency
response families. The current metadata-only mapping covers all 34 rows (100.0%)
and all 8 controlled action categories;
case 454, a canopy-damage near miss without hydrogen release, is linked to a
dedicated structural-damage response family without inferring a hydrogen release.
The audit deliberately excludes HIAD emergency
action and lesson text, so it cannot leak a response answer key.

This improves provenance and scenario coverage for evidence-grounded prompts, but
it does not establish response correctness or operator benefit. The separate
[response-stage contract audit](HIAD_RESPONSE_STAGE_CONTRACT.md) checks that all
34 metadata mappings carry recognition, immediate, stabilization, restart and
prevention stages, and that idle periodic monitoring remains quiet. It is still
an interface/traceability check: it does not read HIAD response text and does not
validate the safety or effectiveness of any step. The independent coordinator
review, holdout response collection and expert rating gates remain required.

The [HIAD accident-response coverage evaluation](HIAD_ACCIDENT_RESPONSE_COVERAGE_EVALUATION.md) additionally checks the 34 public metadata cases one by one: 33 cases with recorded action categories route to staged plans, all 8 categories have zero uncovered case-category pairs, and one case with no recorded category is explicitly marked as not assessed rather than treated as no response. This is structural traceability only; raw action prose is excluded and no effectiveness or safety claim is made.

The restricted local accident casebook now contributes only a de-identified
candidate-family count: 322/322 cases have five non-empty response stages.
Candidate mappings are `gas_release` 305, `hose_connection` 261,
`fueling_fault` 162, `supply_connection` 137, `compressor_thermal` 108,
`relief_discharge` 47, `hydrogen_fire` 27 and `overpressure` 6; 318 cases map
to more than one family. These are coverage counts, not incident frequencies,
and no narrative, site, operator, date or effectiveness claim is exposed.

The [KHK public-report inventory](khk_hydrogen_station_public_reports_inventory_2026_10_04.json) adds official accident and precaution report links for qualitative scenario and response grounding. The [scenario-precedent map](khk_scenario_precedent_map_2026_10_04.json) links the inventory's equipment classes to conservative response families and exposes only counts plus representative citation links to the assistant. It is deliberately excluded from numerical model validation, accident-frequency estimation and the station-to-vehicle full-loop holdout because the public reports do not provide synchronized process traces or complete boundary conditions.

The [runtime precedent-routing audit](runtime_public_accident_precedent_routing_2026_10_07.json)
checks all 23 KHK report records across eight mapped response families. The
runtime resolver reproduces all 42 case-to-family references and delivers 15
representative citations to both the evidence manifest and compact LLM prompt,
with zero count, manifest or prompt-projection failures. An overpressure alarm,
for example, therefore receives overpressure precedents rather than the entire
accident inventory. This remains citation routing only: it does not judge the
historical response, infer causes or frequency, or establish that the suggested
steps improve operator decisions.
