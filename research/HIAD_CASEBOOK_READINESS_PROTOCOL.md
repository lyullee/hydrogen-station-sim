# HIAD casebook readiness protocol

The candidate holdout contains 24 public HIAD HRS cases. The prescreen only
flags possible hindsight leakage; it does not approve or rewrite a vignette.
`scripts/audit_hiad_casebook_readiness.py` records the remaining human and
institutional gates without creating any model responses.

Response collection is allowed only when all candidate vignettes have a coded
non-rating coordinator's decision, every leakage review is complete, and the
institutional ethics status is approved, exempt, or formally not required with
an identifier. The audit output is local-only under `data/` and does not contain
new incident narratives.

A passing readiness result would still not establish SAGA effectiveness or
safety. Those claims require the frozen allocation, retained failed calls, and
independent blinded expert scoring specified by the study protocol.
