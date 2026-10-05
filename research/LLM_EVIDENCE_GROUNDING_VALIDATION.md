# LLM evidence-grounding validation

**Recorded:** 2026-10-05
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
- response evidence identifiers (for example HIAD, H2Tools and ISO mappings)
  included per condition and in an aggregate source list;
- public HIAD action-to-playbook traceability metadata with an explicit
  non-efficacy claim boundary;
- a compact HIAD action taxonomy (eight derived action categories, category
  counts and the action-evidence artifact digest) without raw incident prose;
- public KHK accident-report inventory metadata (23 linked reports, 26 incident
  codes and 8 precaution reports) with citation-only rights and no mirrored PDF
  text;
- a derived KHK scenario-precedent map linking all 23 report records to
  conservative response families with counts and representative citations;
- impact calculation state: `not_requested`, `attempted_no_result`, or
  `calculated`;
- calculated impact basis, input sensor tags, model outputs and threshold
  interpretation limits;
- consequence flow-boundary status, requested process flow, HyRAM modeled flow,
  and an explicit mismatch claim limit when high-pressure choked flow causes
  the physics adapter to recompute the release rate;
- a SHA-256 digest over the canonical manifest contents.

The manifest explicitly states that simulated signals are not field
measurements and that sampled consequence distances are not confirmed safety
distances. An LLM response is not allowed to turn `not_requested` or
`attempted_no_result` into a calculated impact result.

## Checks executed

The following tests passed in the repository virtual environment:

```text
.venv\Scripts\python.exe -m pytest tests/test_llm_grounding.py tests/test_digital_twin_direct_qa.py tests/test_hiad_action_playbook_coverage.py tests/test_hiad_accident_response_coverage_evaluation.py -q
14 passed, 2 warnings

.venv\Scripts\python.exe -m pytest -q
580 passed, 16 warnings
```

The tests verify that normal monitoring keeps impact calculation marked as
`not_requested`, emergency or explicit-impact paths preserve calculated
results and input tags, non-finite values are discarded, the main and sensor
assistant routes remain isolated, and a generated answer cannot negate a
confirmed alarm, gas observation, physical leak or calculated impact.
The manifest digest now also covers the public response-source identifiers, the
HIAD action-to-playbook traceability metadata, the derived HIAD action-category
counts and their artifact digest, and the KHK citation inventory used to ground
the staged action plan. Raw HIAD action prose is never inserted into the live
prompt.

The consequence handoff also records whether a supplied process-flow boundary
was retained.  If HyRAM's high-pressure choked-flow path recomputes a different
release rate, the status and ratio are carried into the impact record and LLM
evidence envelope; the result is explicitly limited to model-bound screening.

## Claim boundary

This is traceability and consistency evidence for the software contract. It
does not validate the underlying hydrogen physics, establish field safety, or
measure SAGA's usefulness, omission rate, unsafe-advice rate, latency, or
operator performance. Those require an independently frozen casebook and
qualified expert review, which remain pending in
`manuscript/ijhe_readiness_audit.json`.


## Public incident traceability follow-up

The reproducible [HIAD-to-playbook coverage audit](HIAD_ACTION_PLAYBOOK_COVERAGE.md)
links 34 public HRS incident/near-miss metadata rows to the current emergency
response families. The current metadata-only mapping covers all 34 rows (100.0%)
and all 8 controlled action categories;
case 454, a canopy-damage near miss without hydrogen release, is linked to a
dedicated structural-damage response family without inferring a hydrogen release.
The audit deliberately excludes HIAD emergency
action and lesson text, so it cannot leak a response answer key.

This improves provenance and scenario coverage for evidence-grounded prompts, but
it does not establish response correctness or operator benefit. The separate
[response-stage contract audit](HIAD_RESPONSE_STAGE_CONTRACT.md) checks that all
34 metadata mappings carry recognition, immediate, stabilization, restart and
prevention stages, and that idle periodic monitoring remains quiet. It is still
an interface/traceability check: it does not read HIAD response text and does not
validate the safety or effectiveness of any step. The independent coordinator
review, holdout response collection and expert rating gates remain required.

The [HIAD accident-response coverage evaluation](HIAD_ACCIDENT_RESPONSE_COVERAGE_EVALUATION.md) additionally checks the 34 public metadata cases one by one: 33 cases with recorded action categories route to staged plans, all 8 categories have zero uncovered case-category pairs, and one case with no recorded category is explicitly marked as not assessed rather than treated as no response. This is structural traceability only; raw action prose is excluded and no effectiveness or safety claim is made.

The [KHK public-report inventory](khk_hydrogen_station_public_reports_inventory_2026_10_04.json) adds official accident and precaution report links for qualitative scenario and response grounding. The [scenario-precedent map](khk_scenario_precedent_map_2026_10_04.json) links the inventory's equipment classes to conservative response families and exposes only counts plus representative citation links to the assistant. It is deliberately excluded from numerical model validation, accident-frequency estimation and the station-to-vehicle full-loop holdout because the public reports do not provide synchronized process traces or complete boundary conditions.
