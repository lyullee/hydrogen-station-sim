# IJHE evidence-readiness audit

- Bounded IJHE submission ready: **False**
- Full user objective ready: **False**
- Goal completion permitted: **False**

| Gate | Status | Claim | Evidence |
|---|---|---|---|
| `tank_external_validation` | **PASS** | Measured-boundary Type-IV tank model is externally evaluated on the frozen public split. | `research\tank_model_validation_v2.json` |
| `active_fill_correction_disclosed` | **PASS** | The post-diagnostic H2P-L29 normalization correction and its downstream effect are disclosed and hash-linked. | `research\h2protocol_active_fill_correction.json` |
| `corrected_closed_loop_internal_evidence` | **PASS** | The corrected development pipeline is retained with its low joint-screen pass fractions and internal-comparison status. | `research\closed_loop_development_v2.json; research\closed_loop_internal_comparison_v2.json` |
| `full_loop_external_validation` | **FAIL** | The complete station controller/cascade/precooler loop meets frozen engineering screens on new external cases. | `data\public_validation\results\closed_loop_external_holdout\validation.json` |
| `full_loop_negative_result_disclosed` | **PASS** | The failed full-loop evaluation is disclosed instead of being hidden. | `manuscript\ijhe_manuscript_draft.tex` |
| `hyram_adapter_verification` | **PASS** | The production adapter is identical to and numerically consistent with HyRAM+ 6.1 within the tested scope. | `research\hyram_adapter_verification.json` |
| `station_consequence_geometry_validation` | **PASS** | Displayed outdoor free-jet screening geometry is traceably checked against geometrically applicable independent data. | `research\consequence_geometry_validation.json` |
| `hiad_protocol_integrity` | **PASS** | The incident decision-support study protocol was hash-locked before outcomes. | `research\hiad_study_protocol_manifest.json` |
| `institutional_ethics_determination` | **PENDING** | The applicable institution has recorded the human-participant determination. | `research\hiad_study_protocol_manifest.json` |
| `hiad_casebook_frozen` | **PENDING** | All 24 holdout incident vignettes passed coordinator leakage review and were frozen. | `data\public_validation\results\hiad_casebook_frozen\casebook_freeze_manifest.json` |
| `hiad_holdout_collection` | **PENDING** | All masked alarm/direct/RAG holdout responses were collected under the frozen protocol. | `data\public_validation\results\hiad_decision\collection_manifest.json` |
| `independent_expert_review_complete` | **PENDING** | Three qualified independent reviewers completed the locked 24-event evaluation. | `data\public_validation\results\hiad_decision\analysis\expert_review_analysis.json` |
| `saga_effectiveness_and_safety_supported` | **PENDING** | Direct SAGA improves expert-rated guidance without higher observed omission or unsafe-advice rates. | `data\public_validation\results\hiad_decision\analysis\expert_review_analysis.json` |
| `preoutcome_design_sensitivity` | **PASS** | The fixed incident-study sample limitations were quantified before outcomes. | `research\hiad_design_sensitivity.json` |
| `ijhe_format_gate` | **PASS** | The manuscript satisfies the explicit IJHE length/front-matter limits checked locally. | `manuscript\ijhe_format_check.json` |
| `ijhe_latex_compilation` | **PENDING** | The exact submitted LaTeX source compiles successfully. | `manuscript\ijhe_compile_status.json` |
| `submission_metadata_and_declarations` | **PENDING** | Every author, affiliation, institutional email and declaration is confirmed. | `manuscript\submission_metadata.json` |
| `software_doi` | **PASS** | The reproducible software release has a persistent DOI. | `CITATION.cff` |

## Blocking bounded-submission gates

- `institutional_ethics_determination`
- `hiad_casebook_frozen`
- `hiad_holdout_collection`
- `independent_expert_review_complete`
- `ijhe_latex_compilation`
- `submission_metadata_and_declarations`

## Blocking full-objective gates

- `institutional_ethics_determination`
- `hiad_casebook_frozen`
- `hiad_holdout_collection`
- `independent_expert_review_complete`
- `ijhe_latex_compilation`
- `submission_metadata_and_declarations`
- `full_loop_external_validation`
- `saga_effectiveness_and_safety_supported`

Only full_user_objective_ready=true permits goal completion. A bounded paper may report negative or limited physics honestly, but it does not satisfy the full validated-digital-twin objective.
