# HIAD coordinator review handoff

The HIAD holdout contains 24 public hydrogen-refuelling-station incident
vignettes. Before collecting model responses, a qualified non-rating
coordinator must check each vignette for hindsight leakage: completed emergency
actions, lessons learned, corrective measures, or exact phrases that reveal the
reference response.

The repository includes an advisory prescreen generator. It does not approve,
rewrite, exclude, or freeze any case. The output must remain unresolved until a
coordinator records a coded identity, a KEEP or REWRITE decision, a leakage
confirmation, and notes where residual flags remain.

## Reproduce the handoff

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python.exe scripts\prepare_hiad_coordinator_review.py `
  --casebook data\public_validation\results\hiad_holdout_preparation\casebook_for_approval.json `
  --output data\public_validation\results\hiad_coordinator_prescreen
```

The current prescreen run identified 24 cases: 16 HIGH, 6 MEDIUM and 2 LOW
advisory flags. These are automated screening labels only. The generated HTML
review form keeps coordinator-only reference fields separate from the model
input and exports an approved casebook only after every case is explicitly
reviewed.

The output directory is intentionally excluded from the source distribution
because the casebook and reference response fields are public-evidence working
artifacts rather than a completed blinded evaluation. When a coordinator
returns an approved casebook, run
`scripts/freeze_hiad_approved_casebook.py` and retain the resulting hashes
before collecting any alarm-only, direct-SAGA or standards/RAG responses.

This handoff does not close `hiad_casebook_frozen`,
`hiad_holdout_collection`, `independent_expert_review_complete` or
`saga_effectiveness_and_safety_supported` in the IJHE audit.
