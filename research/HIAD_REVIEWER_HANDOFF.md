# HIAD independent-review handoff

The public HIAD 2.2 incident inventory has a prepared 24-event holdout and an
advisory leakage screen. This handoff records what is ready and what must be
completed by people outside the model-development and response-generation
roles.

## Ready now

1. `data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json`
   contains the frozen 24-event holdout candidates.
2. `data/public_validation/results/hiad_coordinator_prescreen/` contains the
   CSV/HTML advisory review. It flags possible hindsight leakage but does not
   approve or rewrite any vignette.
3. The preregistration, data-management plan, ethics request and reviewer
   information sheet are hash-recorded in
   `hiad_reviewer_handoff_2026_10_04.json`.

## Required human sequence

1. Obtain the institution's ethics/quality determination and complete the
   unresolved institution fields. Until then, recruitment and response
   collection remain prohibited.
2. A qualified non-rating coordinator reviews every case in the HTML screen,
   retains only contemporaneously observable facts, records KEEP/REWRITE and
   exports `approved_holdout_casebook.json`.
3. Run `scripts/freeze_hiad_approved_casebook.py` against the original and
   approved casebooks. The generated freeze manifest must be retained.
4. Package blinded alarm-only, direct-answer and RAG responses with
   `scripts/package_hiad_expert_review.py`, collect all 168 responses, then
   obtain three independent qualified ratings per event and variant.
5. Run `scripts/analyze_hiad_expert_review.py`; only its locked analysis can
   support the SAGA effectiveness/safety gate.

No casebook approval, expert response, safety conclusion or effectiveness
claim is inferred by this handoff. It is a reproducibility aid, not evidence
that the pending gates have passed.
