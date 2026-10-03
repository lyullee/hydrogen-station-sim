# LLM evidence-grounding validation

**Recorded:** 2026-10-03  
**Scope:** digital-twin main assistant and selected-sensor assistant routes

This record documents a software-level grounding check. It is not a human
expert-effectiveness study and does not establish that the assistant improves
operator decisions.

## Contract

Each assistant request now receives an `evidence_manifest` generated from the
same simulator frame used by the deterministic analysis path. The manifest
contains:

- simulation time and an explicit `DIGITAL_TWIN_SIMULATION` source marker;
- sensor tags, values, units and quality status (with a bounded prompt view and
  an omitted-row count);
- active condition labels and associated sensor tags;
- impact calculation state: `not_requested`, `attempted_no_result`, or
  `calculated`;
- calculated impact basis, input sensor tags, model outputs and threshold
  interpretation limits;
- a SHA-256 digest over the canonical manifest contents.

The manifest explicitly states that simulated signals are not field
measurements and that sampled consequence distances are not confirmed safety
distances. An LLM response is not allowed to turn `not_requested` or
`attempted_no_result` into a calculated impact result.

## Checks executed

The following tests passed in the repository virtual environment:

```text
.venv\Scripts\python.exe -m pytest tests/test_llm_grounding.py tests/test_digital_twin_direct_qa.py -q
11 passed, 2 warnings

.venv\Scripts\python.exe -m pytest -q
376 passed, 8 warnings
```

The tests verify that normal monitoring keeps impact calculation marked as
`not_requested`, emergency or explicit-impact paths preserve calculated
results and input tags, non-finite values are discarded, the main and sensor
assistant routes remain isolated, and a generated answer cannot negate a
confirmed alarm, gas observation, physical leak or calculated impact.

## Claim boundary

This is traceability and consistency evidence for the software contract. It
does not validate the underlying hydrogen physics, establish field safety, or
measure SAGA's usefulness, omission rate, unsafe-advice rate, latency, or
operator performance. Those require an independently frozen casebook and
qualified expert review, which remain pending in
`manuscript/ijhe_readiness_audit.json`.


## Public incident traceability follow-up

The reproducible [HIAD-to-playbook coverage audit](HIAD_PLAYBOOK_COVERAGE.md)
links 34 public HRS incident/near-miss metadata rows to the current emergency
response families. The current metadata-only mapping covers 33 rows (97.1%);
case 454, a canopy-damage near miss without hydrogen release, remains unmapped
and is retained as a catalog gap. The audit deliberately excludes HIAD emergency
action and lesson text, so it cannot leak a response answer key.

This improves provenance and scenario coverage for evidence-grounded prompts, but
it does not establish response correctness or operator benefit. The independent
coordinator review, holdout response collection and expert rating gates remain
required.
