# Paper-first status and execution order — 2026-10-12

This note fixes the International Journal of Hydrogen Energy manuscript as the
primary deliverable. It is an evidence map, not a new validation result and it
does not alter model parameters or acceptance thresholds.

## Authoritative status

The current readiness audit records **131 PASS, 10 FAIL and 7 PENDING** out of
148 gates (88.5% gate closure). The declared primary station-side scope is
**130 PASS, 9 FAIL and 2 PENDING** (92.2%). These are bookkeeping ratios, not
probabilities of publication or scientific accuracy.

The bounded submission decision remains **not ready** because eight gates are
open: seven independent physical-transfer screens and the submission metadata
and declarations. The full project objective has one additional open gate for
spatial detector transfer. The synchronized station-to-vehicle full-loop lane
is explicitly outside the primary scope after repeated public-data searches.

## What is already reproducible

- The manuscript format check, 24-page Tectonic compilation, PDF visual check,
  audit-mirror integrity check and six focused paper tests passed in the clean
  reproducibility route (`research/ijhe_reproduction_run_2026_10_12.json`).
- The broad LLM/SAGA, virtual-safety, HAZOP and HIAD software-contract suite
  passed 159 tests with zero failures and two warnings
  (`research/paper_llm_safety_broad_regression_2026_10_12.json`).
- The latest public-data route rechecks found no new rights-cleared,
  common-clock station/controller/dispenser/vehicle logger cohort. Component
  evidence remains usable only within its documented claim boundary.
- The runtime public-evidence envelope now includes a hash-verified aggregate
  of 34 HIAD and 23 KHK incident records. It is used only to ground staged
  response-family traceability; it does not authorize accident reconstruction,
  frequency/risk estimation, consequence-distance validation or operator-
  effectiveness claims.
- A static scan of 1,875 tracked text files and working-tree `.env*` files
  found zero high-confidence secret values. The scan cannot inspect host
  environment variables or git object history; runtime provider keys therefore
  remain environment-only inputs and are not evidence artifacts.

## Highest-impact remaining work

1. Preserve the negative and partial transfer results and finish the reviewer-
   facing tables, uncertainty statements and claim-boundary text for the seven
   open physical screens. A failed screen remains a result; it is not removed
   by retuning after outcome access.
2. Complete author-controlled submission metadata: author names, affiliations,
   corresponding author, funding, acknowledgements, competing interests and
   CRediT roles. These fields cannot be invented from the repository.
3. Re-run the clean reproducibility route after any manuscript-only edit and
   keep the audit counts synchronized with the manuscript.
4. Keep the absence of synchronized station-to-vehicle raw data as an explicit
   limitation. Do not present aggregate operating reports or component traces
   as a full-loop external holdout.

## Ethics and expert-review boundary

The ethics and expert-review item is not a physics or process-validation gate for this paper. The manuscript does not claim improved operator performance, usability, human safety decisions, certification, or autonomous emergency response. Facility-specific ethics determination and qualified independent expert review remain deployment prerequisites because suitability depends on each site's equipment, procedures, evacuation plan, and accountability structure. These reviews do not retroactively turn a failed or pending public-data validation screen into a PASS.

KGS-custodied measurements are used only within the approved de-identified and aggregated scope for baseline data, calibration diagnostics, and model checks. Facility identity, manufacturers, detailed geometry, exact dates, and raw rows remain withheld. The paper therefore describes a research decision-support prototype that requires facility-specific review before deployment.

## Claim boundary for the paper

The paper can make a bounded claim about a reproducible virtual station,
station-side dynamics, selected tank/release/consequence component screens and
traceable machine-level SAGA responses. It cannot claim SAE-compliant fueling
control, site safety certification, autonomous emergency management or improved
human safety decisions without additional evidence and facility-specific review.

The KGS-derived material is reported only as custodian-approved, de-identified
aggregates. Facility identity, dates, manufacturers, equipment identifiers and
detailed geometry remain withheld.

## Evidence index

- `manuscript/ijhe_readiness_audit.json`
- `manuscript/ijhe_manuscript_draft.tex`
- `research/ijhe_reproduction_run_2026_10_12.json`
- `research/paper_llm_safety_broad_regression_2026_10_12.json`
- `research/frontend_regression_test_run_2026_10_12.json` (latest 16-test state-contract run)
- `research/full_python_test_run_2026_10_12.json` (latest full Python run: 1,461 passed, 6 skipped)
- `research/PROGRESS_DELTA_2026_10_12.md`
- `research/public_station_vehicle_search_recheck_2026_10_12.json`
- `research/INCIDENT_EVIDENCE_TRACEABILITY_2026_10_12.md`
