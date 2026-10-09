# LLM Evidence Context and Prompt Budget

## Split responsibilities

The digital twin keeps the complete `h2station.llm-evidence.v1` manifest in
API responses.  It contains all auditable aggregate artifacts, the SHA-256
evidence digest, source limits and calculation provenance.  It is not sent as
an interactive-provider prompt payload because it can exceed a practical chat
context budget.

`prompt_decision_evidence()` creates the provider-facing projection.  It
contains only:

- simulation and calibration status;
- detector policy thresholds;
- the current consequence result and its validation boundary;
- a bounded public operating-envelope comparison;
- aggregate incident-response evidence; and
- explicit station-to-vehicle, source-depletion and aperture-model claim
  limits.

It also includes a compact, aggregate `validation_readiness` projection from
`manuscript/ijhe_readiness_audit.json`.  The projection carries the gate counts,
ledger-integrity status, full-loop support flag and claim boundary; it contains
no source paths, private identifiers or raw measurement rows.  The ledger is
authoritative for the downstream claim guard, so a stale permissive manifest
cannot re-enable an unsupported full-loop statement.

On the current reproducible manifest, the full audit object is about 45.7 kB
when JSON encoded; the decision envelope is kept below 3.5 kB.  The SHA-256
digest is retained so the compact prompt can be related to the complete API
manifest without sending restricted data to a provider.

## Live-signal priority

For the main operator assistant, alarm- and question-related sensor tags,
active detector tags and reference tags are sent first.  A deterministic
sample is then capped at 48 sensor rows.  The full frame remains available to
the simulator and API callers.

For the selected-sensor assistant, current sensor value, gas observation,
active/retained alarm state, simulated release evidence and calculated impact
are placed before the prompt-only action summary.  This prevents an extensive
response playbook from pushing a live release or gas-detection field beyond
the provider prompt cap.

## Response-plan handling

The LLM receives the first immediate and stabilization steps for context.
The complete versioned five-stage response plan remains deterministic: it is
returned separately as `response_guidance` and appended to the Korean operator
view.  A provider therefore cannot omit the plan, and cannot replace it with
an invented procedure.

## Boundaries

This optimisation changes neither model physics nor validation claims.  The
complete evidence manifest remains the audit record; the response is still
post-checked by `guard_llm_claims`.  The compact envelope retains the failed
frozen station-to-vehicle screen and the prohibition on treating a modeled
range as a site safety or evacuation distance.
