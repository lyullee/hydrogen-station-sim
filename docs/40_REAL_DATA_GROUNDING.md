# Real-data grounding in runtime decision support

The simulator now carries a compact public-source index with each LLM evidence
header. The index is built only from evidence records that passed their local
provenance checks and contains a title, an inspectable URL, and the limited
purpose for which the source may be used. Current entries cover:

- NREL H2FillS and DOE/NREL high-flow fueling experiments for pressure, flow,
  temperature, and fill-duration operating-range context.
- The public HITRF facility description for storage tiers, compressor stages,
  and precooling scale context. It is not a synchronized logger archive.
- KHK public hydrogen-incident reports for qualitative scenario and response
  precedent.
- A licensed accidental-release dataset and an open detector-dispersion
  dataset for release/ignition wording and detector persistence replay.
- The public Grune/Sempert confined-space ventilation archive. Its 42 measured
  spatial profiles are reduced to no-wind-normalized factors by release size,
  flow and wind mode. These factors are applied only to the virtual detector
  proxy; they are not used as a CFD field, detector-placement certification or
  station-scale validation.
- The same USN/FFI concentration traces are also reduced to a robust
  22-case scale coefficient (`28.4495 vol% H₂ per g/s`). It replaces the old
  arbitrary `mass_flow × 10000` conversion in the advisory virtual detector.
  The coefficient is the median of each case's final-third, sensor-grid P90
  concentration divided by its measured mean release flow. Ventilation and
  wind factors remain separate, and concentrations are clipped to 100 vol%.
  This is a bounded open-channel proxy only; it is not an outdoor dispersion,
  detector-placement, ESD, or consequence-distance validation.

The links are placed in `prompt_evidence_header()` and
`prompt_evidence_summary()` as `public_source_links`. This makes the sources
available to the main and sensor assistants without copying private rows into
the prompt. Private station logs remain represented only by de-identified
quality and calibration metadata; no operator, site, date, manufacturer,
tag, or raw row is exposed.

Generated text is bounded a second time after the provider returns. The
`guard_llm_claims()` post-processor reads the same evidence manifest and
replaces positive claims of full-loop field validation, safety certification,
or a confirmed evacuation/safety distance when those gates are false. An
explicit limitation such as “this is not field validation” is preserved, as
are measured observations, calculated sample distances, and the staged
response plan. Each API answer exposes the small `llm_claim_guard` audit record
so a replay can show whether a provider overclaim was filtered.

The private schema intake also carries a privacy-bounded family summary for
compressor/station pressure and temperature, flow/totalizer, valve/alarm and
lifecycle channels. The current archive contains zero vehicle-side channel
families, so the assistant keeps station-boundary calibration separate from
vehicle-fill or station-to-vehicle accuracy claims.

A broader local discovery pass confirms that data volume is not the limiting
factor. The privacy-bounded inventory contains 33 CSV files (4.749 GiB),
59,272,300 physical rows after one header per file, and 56,854,143 rows after
excluding one exact duplicate payload. Twenty-five files use the narrow schema
and eight use the wide equipment schema. The same aggregate supports 16,770
ordered high-bank pressure cycles, 11,770 paired medium/high episodes, 1,418
short-horizon forecast cases and 733 conditional recharge-flow episodes. None
of this establishes synchronized vehicle tank pressure, temperature, delivered
mass or SOC. The privacy-safe aggregate is recorded in
`research/local_confidential_station_data_utilization_2026_10_08.json`; all
private paths, filenames, headers and raw content remain outside the
repository.

The discovery step is reproducible for future owner-controlled exports with
`scripts/scan_local_workspace_candidates.py`. It accepts one or more local
roots and writes aggregate file, header-family and coarse-candidate counts
only. It deliberately treats keyword/header matches as discovery evidence,
never as validation eligibility; a separate custodian attestation is required
before any candidate can enter a prospective split.

The same scanner was applied to the locally cached public-validation corpus.
It enumerated 263 machine-readable files and screened 159 CSV/TSV headers.
Fifty-eight candidates were release-rig/jet experiments. The only two
vehicle/dispenser keyword matches were static QRA result tables without a
common time axis, and no synchronized vehicle pressure-temperature-flow
candidate was promoted. The aggregate result is retained in
`research/local_public_candidate_scan_2026_10_09.json`; this prevents a static
consequence table from being misrepresented as measured fueling telemetry.

The accompanying custodian description now attests two storage-pressure roles
and two lifecycle-counter roles at aggregate level. This closes the role-mapping
gap for the pressure-cycle and cascade-sequence cohorts without publishing
source tags or identity. Flow units, totalizer reset semantics and vehicle-side
channels remain unverified, so absolute mass-flow fitting, SOC validation and
automatic runtime retuning remain disabled. See
`research/local_station_semantic_attestation_2026_10_09.json`.

The aggregate utilization record is now carried into the LLM evidence envelope
as `confidential_local_station_data_utilization`. The main and sensor assistants
can therefore distinguish “the station archive is large and dynamically useful”
from “a complete station-to-vehicle validation exists.” The compact interactive
projection exposes only deduplicated row count, selected station-side cohort
counts, readiness flags and the claim boundary; the detailed header remains
available for audit/UI consumers. It cannot promote an unconfirmed channel
meaning, fit a safety limit or authorize vehicle/full-loop claims.

The same privacy boundary is available at runtime through
`GET /api/evidence/local-station` and is included in `GET /api/health` as
`local_evidence`. This endpoint reads only the committed aggregate audit
artifacts. It reports station-side coverage, continuity quality and the
full-loop decision; it fails closed when an artifact is missing or malformed.
It never returns raw rows, source paths, filenames, headers, identifiers or
site metadata, so a UI can show the evidence scope without turning a local
archive into a public data export.

The wider local workspace was also screened for adjacent hydrogen-process
material. A hydrogen-city/pipeline process collection contains 18 event logs
with 2,411,774 numeric rows, pressure/temperature/flow-like and state-like
families, plus 19 workbooks. Its local index documents millisecond Unix epoch
timestamps and a KST conversion rule, but the event rows are interleaved across
entities and keys and still require per-channel semantic attestation. A
separate liquid-hydrogen-centre collection contributes 52 scenario rows and 17
workbooks. These are useful process-context and virtual response candidates,
not H70 station-to-vehicle fills; the scan found zero eligible synchronized
station-dispenser-vehicle cohorts. They therefore remain outside automatic
HRS runtime fitting and full-loop validation. See
`research/LOCAL_ADJACENT_HYDROGEN_DATA_DISCOVERY_2026_10_09.md` and its
privacy-bounded JSON companion.

A full header-only pass over the broader local document collection screened
38,528 machine-readable files and 12,804 CSV/TSV headers. It produced many
vehicle/dispenser keyword hits, mostly from LH2, pipeline, component and
derived-output material; a refined screen found zero files with the complete
time-plus-pressure-plus-temperature-plus-flow/mass header combination. The
aggregate is recorded in
`research/LOCAL_DOCUDATA_FULL_DISCOVERY_2026_10_09.md`. This confirms that
the archive is not small while preserving the stricter full-loop eligibility
boundary.

The adjacent process inventory is now also available to the runtime as a
privacy-bounded context record. It covers 18 hydrogen-city/pipeline event logs
(2,411,774 rows), 273 logical keys and 19 workbooks, plus a smaller liquid-
hydrogen-centre scenario collection. The evidence is useful for sequence,
upstream-utility and HAZOP plausibility discussions only. The main assistant
receives the counts and the explicit `runtime_parameter_application=false` and
`station_to_vehicle_full_loop_validation=false` boundaries; raw paths,
headers, identifiers, values and dates never enter the prompt. This avoids the
previous ambiguity where a large adjacent corpus could be mistaken for an HRS
vehicle-fill trace.

The 25 narrow exports are now structurally recovered without disclosing their
headers. Twelve files contain 29,361,269 rows in a pressure/flow candidate
schema; thirteen contain 29,257,564 rows in a thermal candidate schema. Their
time coverage overlaps by 99.7837%, and every file has a one-second median
sample period. A 600-row diagnostic sample retained 97,709 rows. The final 30%
medians of both flow-like candidates, four pressure candidates and five
temperature-like candidates all remained inside the first 70% P05--P95
envelopes. The lower/medium/high pressure-candidate ordering held for 99.9142%
of the pressure/flow samples. This is recorded in
`research/confidential_station_history_hypothesis_2026_10_08.json`. Cumulative
counters were excluded from the stability decision because their later values
are expected to increase. Flow/totalizer units and temperature roles remain
unattested, so runtime fitting and vehicle/full-loop claims remain disabled.

The pressure-role attestation also permits a bounded test of the already
existing 4.5 MPa high-bank recharge restart margin. Two initial methods
retained zero cycles because the 12 source histories run newest-to-oldest. That
failure was preserved, the source-order defect was disclosed, and a third
hash-locked protocol froze ascending timestamp sorting before any ordered
cycle outcome was viewed. It recovered 11,565 calibration and 5,205 holdout
cycles. The holdout pressure-drop distribution was 1.13894/4.6378/9.02996 MPa
at P10/median/P90; 4.5 MPa was inside that interval, 2.97% from the median, and
the calibration-to-holdout median shift was 1.01%. This corroborates the
existing development default across two formats in the same archive. It does
not change runtime parameters or establish independent, vehicle-fill,
full-loop, safety-limit or field-certification evidence. Protocol and result
are recorded in
`research/confidential_station_ordered_pressure_cycle_protocol_2026_10_08.json`
and
`research/confidential_station_ordered_pressure_cycle_holdout_2026_10_08.json`.

The owner-attested medium and high pressure roles also enabled a separate
prospective controller-structure test. Before viewing their joint outcomes,
the evaluator froze the cycle detector, one-to-one event pairing window,
70/30 split and all eligibility and sequence screens. It retained 8,106
calibration and 3,664 holdout pairs across all 12 matching histories. Holdout
pair coverage was 70.3939%, and 94.3777% of paired events followed the declared
medium-to-high order; the 80-second holdout median handoff gap remained inside
the calibration P10--P90 range. Every frozen screen passed. This corroborates
the simulator's medium-to-high cascade controller structure within the same
site archive, but it does not uniquely identify vehicle fills because no
synchronized vehicle, dispenser or valve-state channel is present. It does
not validate the low bank, a complete station-to-vehicle loop, a safety limit
or a runtime parameter. The frozen protocol and result are recorded in
`research/confidential_station_cascade_sequence_protocol_2026_10_08.json` and
`research/confidential_station_cascade_sequence_holdout_2026_10_08.json`.

The same owner-attested pressure roles and compressor-load state now support a
separate prospectively frozen short-horizon forecast. The evaluator splits
each trace chronologically before extracting cases, uses only the first 10 s
of a loaded-compressor window to identify the responding bank, and predicts
the following 30 s with a bank-specific robust continuation gain fitted on the
earlier 70%. Across eight equipment logs, 1,024 calibration cases and 394
holdout cases were retained. Holdout median absolute pressure-increment error
was 0.055 MPa, P90 error was 0.529255 MPa, and MAE improved by 71.8855% over a
zero-change persistence forecast; every frozen eligibility, error, direction
and gain-stability screen passed. This establishes same-site short-horizon
station pressure-response evidence only. It does not fit compressor capacity
or vessel geometry, validate a vehicle fill or full loop, change a runtime
parameter, establish a safety limit, or supply independent-site validation.
The protocol and aggregate result are recorded in
`research/confidential_station_recharge_pressure_forecast_protocol_2026_10_08.json`
and
`research/confidential_station_recharge_pressure_forecast_holdout_2026_10_08.json`.

A value-level, pre-attestation consistency screen now tests whether the
unlabelled flow-like channels contain internally coherent instantaneous
flow/cumulative-totalizer pairs. It inspected 3,053,442 sampled rows from 20
pressure-and-flow tables without persisting source paths, tags, timestamps or
rows. The revised fixed-window screen accounts for logger quantization by
testing 1, 10, 30 and 60 second mass-balance windows. Twenty-seven of 54
candidate comparisons in 17 files passed the joint correlation and normalized
error screen. Their median correlation was 0.9971, median span-normalized RMSE
was 2.54%, median selected window was 60 seconds, and median
derivative-to-signal scale was 0.016648 (close to 1/60). The positive internal
consistency result is retained in
`confidential_station_signal_consistency_screen_2026_10_08.json`. It narrows
the remaining request to custodian confirmation of the generic pair, units,
sign/reset convention and calibration state; absolute flow and storage-volume
fitting remain disabled until that attestation is recorded.

A second privacy-bounded screen links the coherent flow/totalizer pair to
compressor-load feedback without publishing any tag or trace. Seven equipment
tables supplied 567,847 rows and 995 positive-flow intervals; 733 intervals met
the predeclared requirement of at least 10 seconds duration and at least 80%
compressor-load feedback. Their median integrated-signal/totalizer ratio was
0.9909. Under the explicitly conditional assumption that the cumulative unit
is kg, the recharge-flow median was 9.594 g/s with a 6.951--9.916 g/s 10th--90th
percentile range. The reference compressor's first-principles initial value of
8.689 g/s lies within that range, so the default is retained unchanged. This is
recorded in `confidential_station_recharge_flow_screen_2026_10_08.json` as
conditional face validity only; it cannot fit capacity until units and
calibration are attested and cannot validate a vehicle fill.

The previously frozen station thermal method was also executed as an explicitly
unattested mapping-hypothesis diagnostic. Eight equipment logs supplied 653,442
one-second rows. All compressor, cooling-inlet and cooling-outlet medians in the
30% chronological suffix stayed inside their 70% prefix p05--p95 envelopes; the
cooling-active temperature-drop median also stayed inside its prefix envelope,
and neither partition raised a quality warning. The result is recorded in
`confidential_station_thermal_hypothesis_2026_10_08.json`. Because the generic
temperature roles, units, cooling-state value and calibration metadata remain
unattested, this supports numerical stability of the mapping hypothesis only:
no runtime temperature, precooler parameter or thermal validation claim changes.

An additional owner-controlled media drop was screened on 2026-10. It contains
equipment photographs and screen recordings of an Excel/SCADA-style logger.
Those recordings are valuable provenance and may reveal candidate tag families,
but they are not machine-readable traces: the displayed rows cannot establish
engineering units, calibration state, quality semantics, event boundaries or
vehicle/receptacle identity. Nine of the twenty-nine videos also lacked a
decodable stream header during the local media probe. The aggregate result is
kept in
`research/confidential_private_media_intake_assessment_2026_10.json`; no media,
frame, OCR value, source filename or calendar value is copied into the
repository. The media therefore does not change model parameters or the
full-loop validation gate. A custodian-side CSV/XLSX export, tag dictionary,
calibration/uncertainty record, relative-time event markers and reuse terms are
still required before a frozen temporal holdout can be built.

The compact media boundary is now included in the runtime LLM evidence envelope
as `confidential_private_media_intake`. The assistant can therefore state that
the owner supplied screen recordings/photos are provenance or inventory clues,
while `machine_readable_trace_present=false` and
`parameter_fit_permitted=false` prevent a video value from being presented as a
calibrated field measurement. The raw media itself is never sent to the LLM.

The pressure bundle is also summarized by generic channel index. Its two
measured boundary channels have distinct operating envelopes, which is useful
context for the assistant when explaining a bank-specific observation. The
channel-to-bank mapping is withheld and remains unattested in the public
artifact, so these values are diagnostic evidence only and do not retune the
controller automatically.

When a live frame contains a nozzle flow, the evidence envelope also adds
`public_operating_envelope_screen`. It compares the simulated flow with the
published high-flow experiment's aggregate average and peak and labels the
context as idle, below the heavy-duty average, within the reported context, or
above the reported peak. This label is explanatory only and is never used as
an accuracy score or as an automatic controller limit.

The source index does not change the numerical model or turn aggregate public
results into a holdout. The runtime must continue to describe the following
boundaries explicitly:

The 2026-10-06 public-data recheck also inspected the 3Emotion operational-log
record, FCH2RAIL station/vehicle measurements, the FCH2RAIL KPI report, the
H2-Stations API, the IPCEI inventory and the open MetHyTrucks HySam
system-measurement record (Zenodo DOI `10.5281/zenodo.20590842`). HySam's
three CC BY 4.0 workbooks are verified against their published hashes and
provide 0.5 s instrumentation context, but their public metadata do not map
channels to a vehicle/receptacle or protocol state. These sources provide
real-station context or published curves, but no new rights-cleared
synchronized raw station-to-vehicle set. The search record is
`research/public_full_loop_search_recheck_2026_10_06.json`; its negative result
keeps the full-loop gate open rather than converting aggregate or plot-only
evidence into a validation claim.

The Grune-derived envelope is the one bounded exception: it changes the
virtual detector concentration proxy when leak flow, orifice size and wind
direction are available. The factor is nearest-neighbour/interpolated only
inside the measured diameter/flow/mode envelope and falls back to `1.0` for
unrepresented conditions. During an active release the runtime defaults to the
measured upper spatial envelope (`max(median, p90/no-wind-p90)`) so a local
high-concentration point is not hidden by a spatial median. The central
estimate remains selectable for sensitivity runs. This is a conservative
detector-proxy choice, not a detector-placement or outdoor-dispersion claim.
The evidence header exposes the DOI, profile count, factor count, statistic,
and claim boundary so an LLM cannot present it as full-loop validation.

The virtual detector alarm/trip rule is loaded from the hash-checked
`dispersion_detector_logic_validation.json` record when it is available. The
public replay covers 22 instrumented concentration cases using 1.0 vol% H₂
alarm, 2.0 vol% H₂ trip and 0.5 s persistence. Each live frame carries the
policy DOI, thresholds and claim boundary, so the LLM can distinguish a
publicly replayed detector rule from an outdoor detector-placement or ESD
validation. If the record is unavailable, the same values remain an explicit
fallback and the frame reports that provenance status.

The concentration scale is loaded from
`dispersion_concentration_proxy_calibration_2026_10_06.json`. Every HAZOP
frame exposes the artifact, DOI, coefficient, case count, formula and claim
boundary under `virtual_detector_proxy`; the LLM evidence manifest carries the
same record. If the derived artifact is missing, the recorded coefficient is
used only as a deterministic fallback and the status changes to
`PUBLIC_DISPERSION_PROXY_FALLBACK`.

The public Cal State LA back-to-back fueling article is also included as
real-station operating context. It reports multiple daily and back-to-back
fills together with storage pressure, cooling/temperature, thermodynamic and
vehicle-SOC outputs. The public record does not provide a reusable synchronized
row-level archive, so the LLM may use it for scenario and face-validity
context, while the full-loop validation gate remains closed.

The peer-reviewed multi-year Cal State LA operating study is kept separately in
`research/calstate_la_multi_year_aggregate_reference_2026_10_09.json`. It
reports approximate aggregate counts (about 4,500 refueling events and more
than 8,800 kg dispensed over 2016--2020), station domains, and a 2020-Q1
energy range. These values are useful for a station-throughput and site-energy
sanity check and for explaining the scale of storage/compression/dispensing in
the LLM. They are intentionally excluded from parameter fitting, full-loop
holdout scoring, site-specific safety distances, and accident-frequency or
response-effectiveness claims because no synchronized raw station-to-vehicle
logger is publicly released by that record.

The open 3Emotion study is retained in
`research/threeemotion_station_operating_aggregate_reference_2026_10_09.json`.
It provides a second, heavy-duty operating context from operator logs: 350 bar
fuel-cell-bus filling, approximately 12.95 kg average daily mass per bus,
approximately 24-hour refueling cadence and station utilization below 30%.
The article title and abstract describe different station/time scopes, which is
preserved in the artifact rather than silently reconciled. The source is used
only for aggregate throughput/utilization explanations and data-request
triage; it does not support raw-row calibration, vehicle-tank thermal claims or
full-loop validation.

The NREL H2FillS HDVS Type-IV workbook is evaluated separately as a frozen
tank/thermal boundary screen. It contains seven tanks and 351 synchronized
samples with measured pressure, temperature and mass channels. The current
model screen reports pressure RMSE 6.16 MPa, temperature RMSE 4.62 °C and
zero of seven tanks passing the predeclared joint screen; the measured-to-model
EOS-equivalent volume ratio is about 0.91. That ratio is a geometry diagnostic,
not a fitted production correction. The workbook remains local and ignored;
only the aggregate result is exposed to the LLM through
`public_tank_validation_boundary`, with a claim boundary that excludes
station-controller, receptacle and full-loop validation.

The same public workbook also has a separate `public_geometry_sensitivity`
record. It compares the legacy effective volume with an opt-in capacity/EOS
geometry rule: the capacity/EOS variants screen 7/7 tanks, with mean pressure
RMSE of 3.54 MPa (frozen fit) or 0.50 MPa (no volume fit) and mean temperature
RMSE of 4.25--4.18 °C. These are post-access sensitivity results, so the
runtime keeps the existing `reference` default and the LLM labels the
capacity/EOS result as diagnostic only. Before changing a default, the rule
must be frozen before data access and evaluated on an untouched external
holdout.

An additional public HyTF trace is carried as `public_tank_trace_boundary`.
It contains 2,536 synchronized samples from a 70 MPa tank fill with two
pressure channels and fourteen tank thermocouples. Because it has no mass-flow,
vehicle/receptacle, station-controller or ESD channels, it is exposed as a
component-screen candidate only. Its repository commit and file hash are
retained for reproducibility, while raw rows remain outside the prompt and the
full-loop claim remains false.

Each simulation snapshot also carries the selected vehicle geometry basis and
declared capacities into the evidence envelope. This lets the main and sensor
assistants state whether the current run used the `reference` default or the
explicit `capacity_eos` option, instead of silently mixing a sensitivity run
with the default model.

- `measured_boundary_calibration` is opt-in. It applies the de-identified
  station-boundary pressure margin to cascade dispatch and recharge restart
  selection as a conservative lower bound. It never overwrites an operator's
  low/medium/high margin or the stronger high-bank chronology criterion, so
  opting in cannot reintroduce rapid recharge cycling. It does not alter
  vehicle geometry, temperature or flow parameters because those channel roles
  are not attested in the private aggregate.
- When this profile is active, each operator frame also carries a
  `measured_boundary_envelope` scope diagnostic for the simulated source
  pressure. It reports whether that value is inside or outside the observed
  range and the distance to the nearest observed limit. This is an evidence
  boundary check only; it is not a safety limit, trip criterion, bank mapping,
  or vehicle-side validation.
- The private pressure replay supports a station-boundary plausibility check,
  not a station-to-vehicle validation.
- Public aggregate plots and facility ratings support operating-range and
  face-validity explanations, not ESD, controller, accident-frequency,
  consequence-distance, or field-certification claims.

The owner-side recheck is recorded in
`research/confidential_operational_profile_recheck_2026_10_06.json`. It compares
the freshly aggregated, de-identified pressure/time fields with the committed
operational profile. A match confirms provenance consistency only; it does not
replace the profile, change default parameters, or close the station-to-vehicle
validation gate. Unattested temperature, flow and discrete-state fields remain
explicitly omitted from the comparison and from any LLM claim.

The owner-controlled pressure bundle is also summarized by generic storage
role in `confidential_bank_role_pressure_envelopes_2026_10_06.json`. The
artifact keeps only medium/high role P05, median, P95, sampled-row counts and
pressure-ramp/restart-margin diagnostics. It excludes raw tags, site names,
dates and manufacturer information. The LLM receives this envelope so it can
compare a simulated bank pressure with a measured operating range, while
`runtime_parameter_application=false` keeps the evidence diagnostic-only.
The artifact does not attest temperature/flow roles, vehicle-side behavior,
field safety limits, consequence distances or full-loop validation.

Each simulation frame also carries `measured_bank_pressure_envelope` with a
P05--P95 comparison for the generic medium and high banks. It is cached, uses
no raw rows, and remains diagnostic-only: an observed-range excursion is an
investigation cue, not an alarm, trip or safe/unsafe classification.

Completed simulation results also carry `summary.public_benchmark_diagnostics`.
For a 70 MPa-class run this compares the simulated fill duration, maximum
flow, start/end pressure and average pressure-rise rate with the aggregate
DOE/NREL H2IQ high-flow experiment. For a 35 MPa-class run it instead compares
the positive-flow average with the independently reported FCH2RAIL
transportable-HRS range. The status is `operating_range_context`, never
pass/fail validation: these public reports do not provide the synchronized
row-level logs and controller state needed for a holdout. The comparison is
therefore not a controller setpoint, safety limit, or full-loop result; if the
provenance artifact is missing it fails closed to `unavailable` without
changing the physics.

The source list is intentionally deterministic and tested. A missing or
invalid source URL is omitted rather than replaced with an invented citation.
