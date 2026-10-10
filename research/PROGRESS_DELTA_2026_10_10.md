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
