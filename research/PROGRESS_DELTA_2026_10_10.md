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

## Source records

- `research/DATA_COVERAGE_SUMMARY_2026_10_09.md`
- `research/DATA_COVERAGE_SUMMARY_2026_10_10.md`
- `research/ijhe_readiness_audit.json`
- `research/priority_validation_run_2026_10_10.json`
- `research/local_workspace_candidate_scan_recheck_2026_10_10.json`
- `research/nrel_h2fills_geometry_diagnostic_2026_10_10.json`
- `research/h2protocol_capacity_eos_sensitivity_2026_10_10.json`
