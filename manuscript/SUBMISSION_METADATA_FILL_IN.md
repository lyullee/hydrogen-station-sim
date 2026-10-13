# IJHE submission metadata completion sheet

`submission_metadata.json` is intentionally left in `DRAFT_PENDING_AUTHOR_CONFIRMATION` until the authors confirm the fields below. Do not infer names, affiliations, institutional email addresses, funding, conflicts or CRediT roles from repository history.

## Required author confirmation

Fill these values in `manuscript/submission_metadata.json`:

- `authors`: every author in final author order, with `name`, `affiliation`, `orcid` (or `null`) and agreed `credit_roles`.
- `corresponding_author.name`: the corresponding author’s full name.
- `corresponding_author.institution`: the confirmed institution name.
- `corresponding_author.institutional_email`: an institutional address, not a personal address.
- `corresponding_author.orcid`: ORCID if available, otherwise `null`.
- `credit_roles_confirmed`: `true` only after every author approves the listed roles.

## Declarations to approve

Replace the `null` statements and set the matching confirmation flags to `true` only after author review:

- `competing_interests_statement` and `competing_interests_confirmed`
- `funding_statement` and `funding_confirmed`
- `ai_disclosure_statement` and `ai_disclosure_confirmed`
- `data_availability_statement` and `data_availability_statement_confirmed`
- `ethics_statement` and `ethics_statement_confirmed`

The current draft wording preserves the study boundary: confidential station-side records are not redistributed; no synchronized station-to-vehicle raw cohort was identified; and the study does not claim measured improvement in operator response or human safety outcomes. Change that wording only when the final manuscript and author approvals require it.

## Ready-to-lock checklist

Before changing `status` to `READY_FOR_SUBMISSION`, confirm:

1. Every author approved the order, affiliation and CRediT roles.
2. The corresponding author approved responsibility for the submission and supplied an institutional email.
3. Funding and competing-interest statements match the final manuscript.
4. AI-use, data-availability and ethics wording was reviewed against the actual study scope.
5. `python scripts/audit_ijhe_readiness.py --json-output research/ijhe_readiness_audit.json --report-output research/ijhe_readiness_audit.md` reports `submission_metadata_and_declarations` as `PASS`.

This sheet is an author-input aid; it is not evidence that the metadata gate has passed.
