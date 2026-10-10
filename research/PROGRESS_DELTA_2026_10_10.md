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
- `research/nrel_h2fills_geometry_diagnostic_2026_10_10.json`
- `research/h2protocol_capacity_eos_sensitivity_2026_10_10.json`
