# HIAD reviewer packet audit

- Status: **READY_FOR_HUMAN_REVIEW_COLLECTION_BLOCKED**
- Ready for human review: **YES**
- Response collection: **BLOCKED**
- Candidate cases: **24**
- Advisory flags: **{'HIGH': 16, 'MEDIUM': 6, 'LOW': 2}**

## Machine checks

- `required_packet_files_present`: **PASS**
- `casebook_and_review_counts_align`: **PASS**
- `prescreen_hash_links_casebook`: **PASS**
- `prescreen_hash_links_exports`: **PASS**
- `machine_preflight_passes`: **PASS**
- `human_gates_remain_explicit`: **PASS**
- `collection_fails_closed`: **PASS**

The package is ready to hand to a qualified non-rating coordinator, but no machine result closes the ethics, leakage, casebook-freeze, response-collection, or independent-review gates.

## Required human actions

1. Institution records ethics, exemption or not-required determination and identifier.
1. Qualified non-rating coordinator reviews all 24 cases and exports approved_holdout_casebook.json.
1. Freeze the approved casebook with the hash-locked freeze script.
1. Only after the freeze and ethics gate, collect masked holdout responses and obtain independent expert ratings.

This audit verifies packet integrity and fail-closed workflow only. It is not an ethics determination, casebook approval, holdout result, SAGA effectiveness result, safety claim, or publication approval.
