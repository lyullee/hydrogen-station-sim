# Progress delta: previous status vs. 2026-10-10

This record explains why the headline readiness percentage appears unchanged even
though the implementation and evidence surface moved forward. The comparison
uses the previous privacy-bounded summary dated 2026-10-09 and the current
summary dated 2026-10-10.

## What did not change

| Measure | 2026-10-09 | 2026-10-10 | Interpretation |
| --- | ---: | ---: | --- |
| IJHE readiness gates | 127 PASS / 10 FAIL / 7 PENDING | 127 PASS / 10 FAIL / 7 PENDING | No external validation gate was promoted. |
| Bounded IJHE submission ready | false | false | Independent negative/unfinished gates remain. |
| Full user objective ready | false | false | Full-loop, spatial transfer and SAGA effectiveness gates remain open. |
| Primary blocker | Synchronized, attested receiving-vessel/vehicle channels | Synchronized, attested receiving-vessel/vehicle channels | The bottleneck is semantic/provenance completeness, not row count. |

The unchanged gate count is deliberate. New diagnostics, public leads, or
performance fixes cannot be promoted to validation without a frozen protocol,
independent provenance and the required receiving-vessel/controller channels.

## What changed

The current summary has eight evidence-surface entries that were not present in
the previous summary:

- an NREL HDVS partial station-to-tank boundary diagnostic;
- a hash-linked same-site station-side integrated holdout (pressure boundary,
  cascade sequence and recharge-pressure forecast);
- an NBS DC liquid-HRS catalogue access candidate;
- a public Type-I filling thermal diagnostic;
- public field-metrology context;
- actual-hydrogen spatial dispersion/detector-response context;
- a public 70 MPa tank-boundary diagnostic; and
- a public indoor surrogate detector-coordinate diagnostic.

These entries make the usable scope wider and the claim boundary clearer, but
they intentionally do not close the full-loop gate.

The code path also moved independently of the gate count:

- long-running causal pressure forecasting now uses a bounded recent history;
- event-free nominal runs select LSODA while fault/relief/vent/cooling runs keep
  the event-aware BDF path;
- repeated tabulated flow-property lookups are cached;
- the 60-second API smoke benchmark improved from 20.5 s to 12.91 s in the
  recorded comparison (about 37% lower wall time); and
- the parallel P0/P1/P2 priority validation runner passes its focused tracks in
  about 5.5–8.2 s depending on the captured run.

The NREL HDVS work also moved from a generic search lead to a bounded,
hash-identified station-to-tank diagnostic and a separate custodian-data lead.
Its result is retained as a model-repair signal, not as a new holdout.

A further public-source recheck located the open-access Cal State LA HRFF
multi-year study (DOI `10.1016/j.ijhydene.2023.04.084`). It reports roughly
4,500 fills and 8,800 kg dispensed and confirms that station historian data
exist, but the public article exposes aggregate KPIs rather than a reusable,
synchronized vehicle-side logger archive. It is now an explicit custodian
route in the request package; it does not close the full-loop gate.
The same lead is now carried into the LLM candidate-lead manifest with an
explicit `CONTACT_REQUEST_CANDIDATE_ONLY` status, so operator answers can cite
the lead without presenting aggregate KPIs as raw validation.

An additional official NLR H2FillS route was checked against the programme page,
the H2FillS user manual and the fast-flow project description. These records
document an empirical station-to-FCEV validation workflow and the relevant
station, dispenser and vehicle result channels, but downloads require
registration and no reuse-cleared synchronized logger archive was found in the
public pages. The route is now recorded in both request and candidate manifests
as `CONTACT_REQUEST_CANDIDATE_ONLY`; it adds a concrete custodian path without
changing the external-holdout gate.

The official NBSDC liquid-hydrogen station record was then checked through its
public file-tree endpoint. It exposes a concrete seven-file equipment bundle
(two 35 MPa dispensers, a 70 MPa dispenser, a 90 MPa compressor, liquid
pump/storage, high-pressure bank and description document), but the file
endpoint returned an application-required response. The metadata and exact
access result are frozen in
`research/nbsdc_liquid_h2_station_access_recheck_2026_10_10.json`; no raw bytes
were retained and the lead remains request-only.

## Geometry evidence boundary synchronized with LLM grounding

The runtime LLM evidence now carries both public geometry diagnostics instead
of presenting the NREL post-access result in isolation. The NREL H2FillS/HDVS
diagnostic screened 7/7 capacity-EOS cases, while the separate H2Protocol
transfer diagnostic screened 0/8 under the same capacity-EOS rule. Because the
second result is also post-access and not a fresh holdout, the runtime keeps
`reference` geometry as its default, leaves `capacity_eos` opt-in only, and
does not select either variant as an independently validated safety-distance
model. The tank runtime and accident-precedent source-hash audits were
regenerated after this disclosure-only change; readiness remains 127 PASS, 10
FAIL, and 7 PENDING (88.2%).

## P0 request route sharpened

The DOE/NREL heavy-duty fast-flow report is now marked as the highest-priority
custodian route in `research/full_loop_raw_data_request_package_2026_10_05.json`.
The report shows the required station, hose, receptacle, vehicle and mass-flow
channel family in one real H70 experiment, but it does not publish synchronized
rows or reuse terms. The request package now asks specifically for those rows,
bank/precooler/ESD state, J2601-5 inputs, calibration metadata and permission
for derived metrics. This improves the path to the missing P0 evidence without
changing the full-loop gate or the 88.2% headline.

## Local workspace recheck

An expanded privacy-bounded scan of the available ProjectData and DocuData
workspaces screened 52,630 machine-readable files, including 349 spreadsheet
headers. It found **0 full-loop candidates**, 8 partial station/source-boundary
candidates, and no synchronized station/vehicle split pair. The result is
recorded in `research/local_workspace_candidate_scan_recheck_2026_10_10.json`.
This confirms that the current P0 blocker is missing attested receiving-vessel
and controller channels rather than an unsearched local folder. The scanner was
also hardened so malformed workbooks are counted as per-file parse misses
instead of aborting the entire discovery pass.

## Official NBSDC access recheck

The strongest public lead was rechecked through the official NBSDC API without
retaining any workbook bytes. The metadata endpoint returned the declared
35/70 MPa fixed-station record and a two-file package (436.08 KB). The file
tree exposed a station-operation workbook (430,765 bytes) plus its description
document. An unauthenticated request to the official download endpoint
returned a login redirect, so no numerical rows, headers, timestamps or
channel units were inspected. This confirms an authorized-custodian route,
but it does not close the full-loop gate or change the readiness percentage.

## Why this still feels slow

The remaining work is dominated by gates that cannot be manufactured locally:

1. three privacy-safe, common-clock charging events with receiving-vessel
   pressure/temperature and controller/protocol state;
2. independent review and the frozen HIAD/SAGA effectiveness study; and
3. unresolved negative physics gates that require model repairs followed by
   fresh independent replays.

The practical next step is therefore to keep P0 intake, P1 physics repairs and
P2 review work independent. Repeating broad public-data searches without the
missing receiving-vessel/controller boundary will increase documentation but
will not move the readiness count.

## Critical-lane rerun (2026-10-10)

The five-track critical diagnostic lane was rerun in parallel after the NBSDC
access recheck (`research/priority_diagnostic_run_2026_10_10.json`). All child
processes completed in 2.66 s, but the scientific screen remains blocked: the
MC SOC/EOS closure diagnostic passed all 8 cases and the Dickens thermal
sensitivity passed its 3 internal cases, while the MC tank-boundary, H2SAFE
spatial-response and NREL HDVS tank screens remain negative. These are
post-outcome development diagnostics; they do not revise any frozen holdout,
change production parameters or increase the readiness percentage.

## Local archive recheck (2026-10-10)

The owner-controlled archive was re-read outside the repository instead of
being treated as missing data. It contains 33 CSV exports and 59,272,300 rows
(4.749 GiB; 32 unique payloads after duplicate exclusion). The archive is
substantial for station-side pressure/cascade/flow/temperature/controller
analysis, but the header-level screen found no vehicle or receptacle channel.
The result is recorded in
`research/local_confidential_station_data_utilization_2026_10_10.json` and
`research/private_station_pressure_lifecycle_audit_2026_10_10.json`. This
narrows the remaining high-impact request to synchronized receiving-vessel
channels and custodian unit/timebase attestation; it does not justify a
full-loop or safety-distance claim.

## Readiness evidence refresh (2026-10-10)

The readiness audit now selects the newest privacy-bounded local inventory and
the newest Dickens mixed-convection diagnostic when present, while retaining
the older records as fallbacks for older checkouts. The refreshed audit points
to the 2026-10-10 artifacts and still reports **127 PASS / 10 FAIL / 7
PENDING** (88.2% gate closure). The count is unchanged because this closes an
evidence-freshness gap only; it does not promote station-side data to
full-loop validation or change runtime parameters.

## Regression health check (2026-10-10)

The complete repository regression suite passed **1,336 tests** in 219.56 s
with 19 dependency deprecation/physics warnings and no test failures. The
impact-first diagnostic lane remains separate: its five critical processes
complete in about 2.7 s, but the scientific screen still retains the three
negative physics/spatial results described above. This keeps fast diagnosis
available without mistaking a full green software suite for scientific
validation.

## Source records

- `research/DATA_COVERAGE_SUMMARY_2026_10_09.md`
- `research/DATA_COVERAGE_SUMMARY_2026_10_10.md`
- `research/ijhe_readiness_audit.json`
- `research/priority_validation_run_2026_10_10.json`
- `research/priority_diagnostic_run_2026_10_10.json`
- `research/local_workspace_candidate_scan_recheck_2026_10_10.json`
- `research/nrel_h2fills_geometry_diagnostic_2026_10_10.json`
- `research/h2protocol_capacity_eos_sensitivity_2026_10_10.json`
- `research/ijhe_readiness_audit_2026_10_11.json`
- `research/ijhe_readiness_audit_2026_10_11.md`

## Evidence freshness wiring (2026-10-11)

The latest privacy-bounded local-station inventory is now selected first by both
LLM grounding and runtime coverage loading, with the 2026-10-08 artifact retained
as a fallback for older checkouts. A new coverage snapshot was generated without
raw rows or identifying paths and passed the privacy scan. The targeted grounding,
coverage and evidence-API lane passed 32 tests. Re-running the source-hash audits
restored the integrity gates; the readiness audit remains **127 PASS / 10 FAIL / 7
PENDING (88.2% gate closure)**, with bounded and full objective readiness still
false.

## HyTunnel model-form diagnostic (2026-10-11)

Added a separate geometry-declared two-zone source-to-vent development model
(`src/h2station/hytunnel_two_zone_diagnostic.py`) and reran all 18 public
dispersion cases. The model uses the published 5 m source-to-vent-wall distance
and 40 ft enclosure length without outcome fitting. It passes 4/18 cases versus
6/18 for the frozen well-mixed model, so it is retained as a negative diagnostic
(`research/hytunnel_two_zone_diagnostic_2026_10_11.json`) and does not change the
readiness percentage or production parameters. This isolates a useful next
physics requirement: a single source-to-bulk zone is insufficient; a validated
plume/stratification model and sensor-coordinate crosswalk are still needed.
The new module has three focused regression tests; the HyTunnel test lane is
now 9 passed.

The LLM evidence manifest now exposes this negative development diagnostic as a
separate, explicitly non-calibrating field. This prevents a future assistant
response from presenting the two-zone experiment as a validated HRS dispersion
model while still making the model-form finding available for grounded answers.

## Spatial-rank candidate sensitivity (2026-10-11)

A declared post-outcome sensitivity grid over the 18 public actual-hydrogen
HyTunnel spatial cases identified a candidate rank formula with mean top-five
recall **0.744** versus **0.578** for the frozen formula and a same-cohort joint
screen pass. Because the responses were already visible, this does not alter the
frozen gate or runtime routing. The candidate is recorded solely to make the
next independent spatial holdout precise rather than continuing unbounded
coefficient experimentation (`research/hytunnel_spatial_candidate_sensitivity_2026_10_11.json`).

## Critical-lane rerun (2026-10-11)

The impact-first diagnostic lane completed in **2.727 s** after the latest
grounding refresh (`research/priority_diagnostic_run_2026_10_11.json`). The
processes all completed successfully, and the Type-III mixed-convection
diagnostic passed its three declared internal cases. The MC SOC/EOS mass
closure diagnostic also passed all eight cases. The scientific screen still
fails the MC vehicle-tank boundary replay (0/8), H2SAFE spatial-response
diagnostic (0/1), and NREL HDVS tank screen (0/7). These are negative,
post-outcome development results only: they do not alter the frozen holdout,
production parameters, readiness gates, or the 88.2% gate-closure value.

## Restricted recharge-data recheck and intake tightening (2026-10-11)

The owner-controlled refresh of eight station-side traces was re-read in
memory only. Under a **temporary, non-published generic mapping** the earlier
restart-dwell recommendation remained about **290 s**, while the later
chronological segment contained a completed OFF-to-ON interval of about
**176 s**. Because the mapping was not a custodian-signed role/unit map, this
rerun is not validation evidence and was not copied into the repository or
applied to runtime. The existing attested aggregate therefore remains
runtime-ineligible and the default controller is unchanged.

The full-loop request templates now require custodian attestation for generic
channel roles, units and scale/offsets, missing-value codes, discrete active /
inactive / fault values, bank-role mapping, and common-clock alignment before
numerical rows are opened. This prevents inferred tag names from being treated
as full-loop evidence in the next intake.

## Impact-first parallel rerun (2026-10-11)

The critical lane was rerun with five independent diagnostics in parallel and
completed in **2.746 s** (`research/priority_diagnostic_run_2026_10_11_latest.json`).
The process layer was healthy, but the scientific screen remained blocked by the
MC vehicle-tank boundary (0/8), H2SAFE spatial response (0/1), and NREL HDVS
tank screen (0/7). MC SOC/EOS closure (8/8) and the Dickens mixed-convection
diagnostic (3/3) passed. This is the impact-first execution path: independent
checks run together, while negative post-outcome diagnostics remain excluded
from runtime promotion and do not change the readiness percentage.

## Receiving-vessel event-unit audit (2026-10-11)

The local NREL HDVS workbook was rechecked for statistical independence. Its
seven tank channels share one clock and one fill boundary, so they are **one
independent multi-tank event**, not seven independent charging events. The
privacy-bounded result is recorded in
`research/nrel_hdvs_event_unit_audit_2026_10_11.json` and is now exposed to the
LLM evidence summary as `independent_event_count=1`. This tightens claim
wording without changing the negative tank screen or the 88.2% readiness value.

## Impact-first rerun after audit refresh (2026-10-11)

The critical diagnostic lane was rerun after the readiness-audit refresh at
commit `41f93a4`. All five child processes completed in **2.705 s**. The
software/process status remained healthy; the scientific screen remained
blocked by the MC vehicle-tank boundary (0/8), H2SAFE spatial response (0/1),
and NREL HDVS tank boundary (0/7). The MC SOC/EOS boundary (8/8) and Dickens
mixed-convection sensitivity (3/3) remained positive development diagnostics.
The refreshed result is retained in
`research/priority_diagnostic_run_2026_10_11_latest.json`; it does not promote
a frozen validation gate or change the 88.2% headline.

## H2SAFE transfer check for the spatial candidate (2026-10-11)

The post-outcome HyTunnel candidate was applied unchanged to the five public
H2SAFE helium-surrogate traces as a rank-only transfer check. It did not
generalize: nearest-sensor response-quartile fraction was **0.20** for the
candidate versus **0.60** for the frozen baseline, and mean top-five recall was
**0.60** versus **0.56**. The H2SAFE release-to-CSV timing crosswalk is still
absent, so this is not validation and cannot close a gate. The transfer result
is stored in `research/h2safe_spatial_candidate_transfer_diagnostic_2026_10_11.json`,
and the LLM evidence manifest now exposes the negative result so it cannot
recommend the same-cohort candidate as a runtime improvement.

## USN actual-hydrogen spatial response diagnostic (2026-10-11)

The 22 public USN open-channel archives were replayed directly from their ZIP
members using the 29 machine-readable sensor coordinates. The diagnostic uses
the per-sensor q99-minus-q10 hydrogen response and compares a transparent
inverse-distance rank with a downward-release sensitivity rank. The inverse-
distance model reached median Spearman **0.591**, mean top-five response-
quartile recall **0.727**, and nearest-sensor response-quartile fraction
**0.545**; the declared joint screen therefore failed. The downward-release
sensitivity was weaker (median Spearman **0.497**) and also failed. This is
post-access development evidence only: no raw rows are retained, no runtime
parameter is replaced, and no readiness gate is promoted. The result is stored
in `research/usn_actual_h2_spatial_response_diagnostic_2026_10_11.json` and
will be used to freeze the candidate features for a future untouched spatial
holdout.

## Actual-H2 evidence routing (2026-10-11)

The USN diagnostic is now exposed to the LLM evidence manifest, compact
decision projection, provenance summary, and public-source links. The exposed
record is aggregate-only and carries `independent_holdout=false`,
`runtime_parameter_application=false`, and `claim_supported=false`, so an
answer can use the 22-case actual-H2 result as context without presenting it as
detector calibration, safety-distance validation, or station-runtime evidence.
The public tank and accident-precedent hash audits were refreshed after the
grounding change, and the full regression suite remained **1,346 passed / 19
warnings**.

## Dickens Type-III temperature observation diagnostic (2026-10-11)

The frozen Type-III replay was re-integrated with the same unfitted gas,
liner, and shell states and the source-declared mass-flow boundary. A separate
post-outcome diagnostic compares six predefined observation operators for the
published `gas_mean` channel. The gas-state operator retains the frozen
temperature miss, while the diagnostic records the other state combinations as
semantic candidates only; none is selected or promoted. The artifact is
`research/dickens_typeiii_temperature_observation_diagnostic_2026_10_11.json`.
It explicitly preserves the frozen validation result, runtime gas-temperature
state, source hashes, and the prohibition on parameter fitting or operator
selection. The finding narrows the next data request to a measurement-location
and weighting definition, but it does not close the Type-III gate or change the
**127 PASS / 10 FAIL / 7 PENDING (88.2%)** readiness headline.

The bounded LLM evidence now carries this artifact under the existing
temperature-semantic boundary, including its six candidates and non-promotion
flags. This prevents a decision assistant from silently treating a favourable
post-outcome temperature combination as validated physics.

## Final regression after observation-boundary wiring (2026-10-11)

The complete suite passes **1,346 tests / 19 warnings**. The warnings are the
existing Starlette/httpx, HyRAM physics, and workbook-reader deprecations; no
test failures remain. The scientific readiness audit is unchanged at **88.2%**
because this work clarifies evidence semantics rather than promoting a failed
or pending external-validation gate.
