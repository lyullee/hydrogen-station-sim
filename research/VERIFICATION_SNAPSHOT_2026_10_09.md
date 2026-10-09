# Verification snapshot (2026-10-09)

This snapshot records the current reproducibility state after the data-coverage
review. It is a verification record, not a claim that the full station-to-
vehicle objective is complete.

## Executed checks

- Full repository test suite: **1192 passed**, 18 dependency deprecation or
  physics warnings, 0 test failures.
- Focused external-data checks (HyTunnel, Dickens Type-III, data-coverage
  summary): **14 passed**.
- Working tree: clean after the verification run.

## Evidence that is usable now

| Evidence | Current result | Permitted use |
| --- | --- | --- |
| De-identified station logs | 33 CSV files; 56,854,143 deduplicated rows | station-side pressure, cascade and lifecycle diagnostics |
| Same-site pressure forecast | 394 chronological holdout cases; MAE 0.184 MPa; p90 0.529 MPa; direction 94.9% | short-horizon advisory forecast |
| Public Type-IV tank data | 12 measured-boundary cases; runtime match true | Type-IV tank component behavior |
| Public accident precedents | 23 reports routed to 8 response families and 42 runtime references | scenario and response-plan grounding |

## SAGA response contract

The runtime now rejects an incomplete structured emergency plan before it is
returned to the monitor. Every selected plan must contain non-empty
recognition, immediate, stabilization, restart and prevention stages plus an
HTTPS source link; an active alert must also contain common initial steps. This
is a structural safety guard, not an expert-effectiveness or field-safety
claim.

The interactive evidence envelope also carries a compact support-scope
contract: station-side evidence is marked separately from full-loop vehicle
validation, site-specific consequence distance and SAGA effectiveness. The
operator-facing `data_used.support_scope` exposes the same four flags. This
keeps the privacy-bounded station results usable for pressure, cascade and
recharge advice without promoting them into vehicle or field certification.

## Evidence still outside the claim boundary

The synchronized station-to-vehicle external holdout remains unavailable. The
current local station inventory has no attested vehicle-side channel set, and
the public component corpora do not provide a new, rights-cleared gaseous H70
full-loop cohort. The following claims therefore remain disabled:

- prospective full-loop station-to-vehicle accuracy;
- compressor, cascade, dispenser or field safety certification;
- calibrated consequence distances or detector-placement certification;
- SAGA intervention effectiveness.

The current failures in the Dickens Type-III, HyTunnel and other external
component gates are retained as negative evidence. No failed gate was silently
replaced by a post-outcome fit. Development can continue with the available
component and station-side data; only the full-loop gate requires a new
time-synchronized, semantically attested event set.

## Privacy boundary

This record contains no raw rows, source paths, absolute dates, site/company
identity, manufacturer, tag names or equipment identifiers. It does not expose
the confidential station data and does not convert it into a field-safety
claim.
