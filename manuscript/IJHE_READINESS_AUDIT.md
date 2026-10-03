# IJHE evidence-readiness audit

- Bounded IJHE submission ready: **False**
- Full user objective ready: **False**
- Goal completion permitted: **False**

| Gate | Status | Claim | Evidence |
|---|---|---|---|
| `tank_external_validation` | **PASS** | Measured-boundary Type-IV tank model is externally evaluated on the frozen public split. | `research\tank_model_validation_v2.json` |
| `active_fill_correction_disclosed` | **PASS** | The post-diagnostic H2P-L29 normalization correction and its downstream effect are disclosed and hash-linked. | `research\h2protocol_active_fill_correction.json` |
| `corrected_closed_loop_internal_evidence` | **PASS** | The corrected development pipeline is retained with its low joint-screen pass fractions and internal-comparison status. | `research\closed_loop_development_v2.json; research\closed_loop_internal_comparison_v2.json` |
| `partial_station_profile_diagnostic_integrity` | **PASS** | The profiled partial-station experiment is retained as a bounded diagnostic and cannot be mistaken for full-station validation. | `data\public_validation\results\partial_station_profile_diagnostic\validation.json` |
| `mc_source_schedule_diagnostic_integrity` | **PASS** | The consumed MC Default source-pressure and protocol-schedule sensitivity is retained as diagnostic evidence, not external confirmation. | `data\public_validation\results\partial_station_mc_protocol_source3_physics_only\validation.json` |
| `full_loop_external_validation` | **FAIL** | The complete station controller/cascade/precooler loop meets frozen engineering screens on new external cases. | `data\public_validation\results\closed_loop_external_holdout\validation.json; research\external_full_loop_data_search.json` |
| `nrel_h2fills_workbook_provenance_integrity` | **PASS** | The NREL HDVS tank candidate remains byte-identified after a package-container change without being overclaimed as a new full-loop holdout. | `research\nrel_h2fills_package_retrieval_check.json; data\public_validation\results\nrel_h2fills_hdvs_typeiv\validation.json` |
| `full_loop_negative_result_disclosed` | **PASS** | The failed full-loop evaluation is disclosed instead of being hidden. | `manuscript\ijhe_manuscript_draft.tex` |
| `hyram_adapter_verification` | **PASS** | The production adapter is identical to and numerically consistent with HyRAM+ 6.1 within the tested scope. | `research\hyram_adapter_verification.json` |
| `station_consequence_geometry_validation` | **PASS** | Displayed outdoor free-jet screening geometry is traceably checked against geometrically applicable independent data. | `research\consequence_geometry_validation.json` |
| `open_channel_detector_logic_evidence` | **PASS** | Measured open-channel concentration records replay the declared detector threshold and persistence logic with an explicit non-HRS claim boundary. | `research\dispersion_detector_logic_validation.json` |
| `incident_playbook_public_evidence` | **PASS** | High-consequence playbooks expose the public HIAD 2.2 accident/near-miss source alongside standards guidance. | `src\h2station\data\emergency_playbooks.json` |
| `public_dispenser_endpoint_diagnostic` | **PASS** | Public 35/70 MPa dispenser endpoint tables are replayed as an explicit negative diagnostic without being promoted to full-loop validation. | `research\cip_dispenser_endpoint_screen.json` |
| `preslhy_blowdown_external_validation` | **FAIL** | The source-depletion and direct-aperture release model meets its prospectively frozen screens on public PRESLHY ambient blowdown experiments. | `research\preslhy_blowdown_external_validation.json; research\preslhy_blowdown_validation_protocol.json` |
| `preslhy_revised_holdout_validation` | **FAIL** | The revised non-adiabatic source-depletion model meets the prospectively frozen PRESLHY E5.1 holdout rule. | `research\preslhy_e5_1_holdout_result.json; research\preslhy_e5_1_holdout_protocol.json` |
| `proust_independent_release_validation` | **FAIL** | The fixed high-pressure aperture relation meets its prospectively frozen rule on the independent INERIS/CEA 90 MPa campaign. | `research\proust_release_holdout_result.json; research\proust_release_holdout_protocol.json; data\public_validation\derived\proust_90mpa_release.csv` |
| `release_network_development_integrity` | **PASS** | The post-outcome release-network diagnostic is retained as consumed development evidence and cannot be mistaken for validation. | `research\release_network_development.json` |
| `schefer_transient_release_validation` | **FAIL** | The locked adiabatic vessel-discharge model meets all frozen transient mass-flow screens on the independent Sandia/SRI experiment. | `research\schefer_2006_holdout_result.json; research\schefer_2006_holdout_protocol.json; data\public_validation\derived\schefer_2006_figure3b.csv` |
| `schefer_2007_pressure_decay_validation` | **FAIL** | The locked adiabatic vessel-discharge model meets all frozen pressure-decay screens on the independent Schefer et al. 2007 experiment. | `research\schefer_2007_holdout_result.json; research\schefer_2007_holdout_protocol.json; data\public_validation\derived\schefer_2007_figure4.csv` |
| `grune_2014_pressure_decay_validation` | **PENDING** | The locked source model meets all pressure-decay screens on the independent KIT small-reservoir release. | `research\grune_2014_holdout_result.json; research\grune_2014_holdout_protocol.json; data\public_validation\derived\grune_2014_figure2.csv` |
| `ekoto_transient_release_validation` | **PASS** | The locked adiabatic vessel-discharge model meets all frozen transient mass-flow screens on the independent Ekoto et al. scaled release. | `research\ekoto_2012_holdout_result.json; research\ekoto_2012_holdout_protocol.json; data\public_validation\derived\ekoto_2012_figure3.csv` |
| `hiad_protocol_integrity` | **PASS** | The incident decision-support study protocol was hash-locked before outcomes. | `research\hiad_study_protocol_manifest.json` |
| `institutional_ethics_determination` | **PENDING** | The applicable institution has recorded the human-participant determination. | `research\hiad_study_protocol_manifest.json` |
| `hiad_casebook_frozen` | **PENDING** | All 24 holdout incident vignettes passed coordinator leakage review and were frozen. | `data\public_validation\results\hiad_casebook_frozen\casebook_freeze_manifest.json` |
| `hiad_public_evidence_inventory` | **PASS** | The public HIAD 2.2 HRS incident subset is hash-linked and reproducibly summarized without leaking blinded responses. | `research\hiad_hrs_public_evidence.json` |
| `hiad_holdout_collection` | **PENDING** | All masked alarm/direct/RAG holdout responses were collected under the frozen protocol. | `data\public_validation\results\hiad_decision\collection_manifest.json` |
| `independent_expert_review_complete` | **PENDING** | Three qualified independent reviewers completed the locked 24-event evaluation. | `data\public_validation\results\hiad_decision\analysis\expert_review_analysis.json` |
| `saga_effectiveness_and_safety_supported` | **PENDING** | Direct SAGA improves expert-rated guidance without higher observed omission or unsafe-advice rates. | `data\public_validation\results\hiad_decision\analysis\expert_review_analysis.json` |
| `llm_evidence_grounding_contract` | **PASS** | Main and selected-sensor assistants receive traceable evidence with explicit calculation and uncertainty status. | `research\llm_evidence_grounding_validation.json` |
| `preoutcome_design_sensitivity` | **PASS** | The fixed incident-study sample limitations were quantified before outcomes. | `research\hiad_design_sensitivity.json` |
| `ijhe_format_gate` | **PASS** | The manuscript satisfies the explicit IJHE length/front-matter limits checked locally. | `manuscript\ijhe_format_check.json` |
| `ijhe_latex_compilation` | **PASS** | The exact submitted LaTeX source compiles successfully. | `manuscript\ijhe_compile_status.json` |
| `submission_metadata_and_declarations` | **PENDING** | Every author, affiliation, institutional email and declaration is confirmed. | `manuscript\submission_metadata.json` |
| `software_doi` | **PASS** | The reproducible software release has a persistent DOI. | `CITATION.cff` |

## Blocking bounded-submission gates

- `preslhy_blowdown_external_validation`
- `preslhy_revised_holdout_validation`
- `proust_independent_release_validation`
- `schefer_transient_release_validation`
- `schefer_2007_pressure_decay_validation`
- `grune_2014_pressure_decay_validation`
- `institutional_ethics_determination`
- `hiad_casebook_frozen`
- `hiad_holdout_collection`
- `independent_expert_review_complete`
- `submission_metadata_and_declarations`

## Blocking full-objective gates

- `preslhy_blowdown_external_validation`
- `preslhy_revised_holdout_validation`
- `proust_independent_release_validation`
- `schefer_transient_release_validation`
- `schefer_2007_pressure_decay_validation`
- `grune_2014_pressure_decay_validation`
- `institutional_ethics_determination`
- `hiad_casebook_frozen`
- `hiad_holdout_collection`
- `independent_expert_review_complete`
- `submission_metadata_and_declarations`
- `full_loop_external_validation`
- `saga_effectiveness_and_safety_supported`

Only full_user_objective_ready=true permits goal completion. A bounded paper may report negative or limited physics honestly, but it does not satisfy the full validated-digital-twin objective.
