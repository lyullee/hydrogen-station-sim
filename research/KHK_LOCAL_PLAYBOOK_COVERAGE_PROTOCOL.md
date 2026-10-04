# KHK local candidate-to-playbook coverage protocol

`scripts/audit_khk_local_casebook_playbook_coverage.py` reads the locally
generated casebook from `prepare_khk_local_casebook.py` and checks that every
candidate incident references at least one registered response family. Every
referenced family must contain the five operator-facing stages:

1. recognition;
2. immediate action;
3. stabilization;
4. restart prerequisites; and
5. prevention and safety management.

The casebook, incident descriptions, and audit output are intentionally written
only below the gitignored `data/` directory. KHK/METI access restrictions do not
allow the source workbook or a derived casebook to be committed, mirrored, or
published. The audit therefore records only local hashes and aggregate contract
status when used in a private study log.

A passing contract is an interface traceability result. It does not establish
that a response is correct, safe, effective, statistically representative, or
appropriate for a particular site. Written permission, coordinator approval,
blinded expert scoring, and an independently frozen protocol are still required
before using these records as public IJHE validation evidence.
