# IJHE evidence-readiness audit

Target journal: **International Journal of Hydrogen Energy** (ISSN 0360-3199). See the [publisher scope](https://shop.elsevier.com/journals/international-journal-of-hydrogen-energy/0360-3199), [Guide for Authors](https://www.elsevier.com/journals/international-journal-of-hydrogen-energy/0360-3199/guide-for-authors) and [Elsevier data-statement guidance](https://www.elsevier.com/researcher/author/tools-and-resources/research-data/data-statement).
The local result is an evidence-readiness gate, not a guarantee of editorial acceptance.

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
| `mc_tank_boundary_diagnostic_integrity` | **PASS** | The MC Default measured-boundary replay isolates vehicle-tank thermodynamics from station control without being promoted to full-loop validation. | `research\mc_tank_boundary_diagnostic_2026_10_05.json` |
| `full_loop_external_validation` | **FAIL** | The complete station controller/cascade/precooler loop meets frozen engineering screens on new external cases. | `data\public_validation\results\closed_loop_external_holdout\validation.json; research\external_full_loop_data_search.json; research\public_full_loop_search_recheck_2026_10_04.json; research\public_operational_benchmark_recheck_2026_10_05.json` |
| `real_station_article_boundary_integrity` | **PASS** | The public BAM/KETI field-validation article is recorded as an auditable real-station context and data-request lead without being promoted to raw full-loop validation. | `research\keti_bam_hrs_article_data_boundary_2026_10_05.json` |
| `kgs_real_station_access_boundary_integrity` | **PASS** | The KGS-linked real-station fueling study is retained as a high-value acquisition lead with an independently recorded anonymous-access boundary. | `research\kgs_hrs_code_access_recheck_2026_10_05.json` |
| `jetfire_supplement_rights_boundary_integrity` | **PASS** | The publicly reachable IJHE jet-fire supplement is traceable without treating a rights-uncleared plot artifact as validation data. | `research\carboni_2022_jetfire_supplement_data_boundary_2026_10_05.json` |
| `calstate_back_to_back_article_boundary_integrity` | **PASS** | The Cal State LA back-to-back fueling article is recorded as real-station context without promoting non-public operator logs to validation data. | `research\calstate_la_back_to_back_article_data_boundary_2026_10_05.json` |
| `closed_loop_temperature_stop_diagnostic` | **PASS** | The post-outcome temperature-stop sensitivity is archived without changing the frozen external validation decision. | `research\closed_loop_temperature_stop_diagnostic_2026_10_04.json` |
| `validation_data_acquisition_tracker` | **PASS** | Independent raw-data acquisition routes are recorded with acceptance, rights and claim-boundary checks without treating requests as evidence. | `research\validation_data_acquisition_tracker.json` |
| `byrnes_zenodo_exploratory_screen_integrity` | **PASS** | The newly located open Byrnes hydrogen-release archive is replayed as transparent post-access exploratory evidence without being promoted to validation. | `research\byrnes_zenodo_exploratory_protocol.json; research\byrnes_zenodo_exploratory_result.json` |
| `zenodo_4106101_pressure_peaking_screen_integrity` | **PASS** | The prospective Zenodo pressure-peaking screen is reproducible and remains explicitly exploratory rather than full-loop validation. | `research\zenodo_4106101_pressure_peaking_protocol.json; research\zenodo_4106101_pressure_peaking_result.json` |
| `elvhys_auxiliary_replay_integrity` | **PASS** | The public ELVHYS cryogenic pressure-peaking subset is hash-identified and replayed with a strict non-validation claim boundary. | `research\elvhys_auxiliary_replay.json` |
| `elvhys_dataverse_metadata_integrity` | **PASS** | The CC0 ELVHYS consequence archive has a file-level manifest, channel/timebase checks and an explicit cryogenic component-only boundary. | `research\elvhys_dataverse_metadata_audit_2026_10_05.json` |
| `nrel_h2fills_workbook_provenance_integrity` | **PASS** | The NREL HDVS tank candidate remains byte-identified after a package-container change without being overclaimed as a new full-loop holdout. | `research\nrel_h2fills_package_retrieval_check.json; data\public_validation\results\nrel_h2fills_hdvs_typeiv\validation.json` |
| `full_loop_negative_result_disclosed` | **PASS** | The failed full-loop evaluation is disclosed instead of being hidden. | `manuscript\ijhe_manuscript_draft.tex` |
| `hyram_adapter_verification` | **PASS** | The production adapter is identical to and numerically consistent with HyRAM+ 6.1 within the tested scope. | `research\hyram_adapter_verification.json` |
| `station_consequence_geometry_validation` | **PASS** | Displayed outdoor free-jet screening geometry is traceably checked against geometrically applicable independent data. | `research\consequence_geometry_validation.json` |
| `open_channel_detector_logic_evidence` | **PASS** | Measured open-channel concentration records replay the declared detector threshold and persistence logic with an explicit non-HRS claim boundary. | `research\dispersion_detector_logic_validation.json` |
| `incident_playbook_public_evidence` | **PASS** | High-consequence playbooks expose the public HIAD 2.2 accident/near-miss source alongside standards guidance. | `src\h2station\data\emergency_playbooks.json` |
| `hiad_response_stage_contract` | **PASS** | Public HIAD metadata mappings carry five staged response fields and keep idle periodic monitoring quiet. | `research\hiad_response_stage_contract.json` |
| `hiad_action_evidence_integrity` | **PASS** | The public HIAD HRS action fields are summarized into a non-evaluative, traceable action taxonomy for evidence-grounded guidance. | `research\hiad_action_evidence.json` |
| `hiad_action_playbook_traceability` | **PASS** | All public HIAD action categories are traceably connected to complete staged response plans without claiming efficacy. | `research\hiad_action_playbook_coverage.json` |
| `public_dispenser_endpoint_diagnostic` | **PASS** | Public 35/70 MPa dispenser endpoint tables are replayed as an explicit negative diagnostic without being promoted to full-loop validation. | `research\cip_dispenser_endpoint_screen.json` |
| `accidental_release_ignition_public_evidence` | **PASS** | An openly licensed controlled high-pressure hydrogen breach experiment is captured for accident-like consequence and ignition scenario grounding without being misrepresented as station validation. | `research\accidental_self_ignition_public_evidence_2026_10_04.json` |
| `thermal_effects_public_protocol_integrity` | **PASS** | The independent public ignited-release thermal-effects archive is prospectively frozen as a consequence-only screen. | `research\thermal_effects_ignited_release_protocol_2026_10_04.json` |
| `thermal_effects_public_archive_replay` | **PASS** | All eight public ignited-release MAT files were parsed under one deterministic descriptive extraction rule. | `research\thermal_effects_archive_replay_2026_10_04.json` |
| `thermal_effects_postfreeze_integrity_replay` | **PASS** | The post-freeze thermal archive audit verifies every public case, time base, channel inventory and claim boundary without promoting it to predictive station validation. | `research\thermal_effects_ignited_release_result_2026_10_05.json` |
| `khk_public_accident_report_inventory` | **PASS** | Public KHK hydrogen accident reports are inventoried for traceable qualitative scenario and response grounding without being misrepresented as numerical validation data. | `research\khk_hydrogen_station_public_reports_inventory_2026_10_04.json` |
| `khk_public_accident_report_access_verification` | **PASS** | All inventoried KHK accident-report links resolve to PDF files whose provenance is hash-locked without redistributing the reports. | `research\khk_public_reports_access_verification_2026_10_04.json` |
| `preslhy_blowdown_external_validation` | **FAIL** | The source-depletion and direct-aperture release model meets its prospectively frozen screens on public PRESLHY ambient blowdown experiments. | `research\preslhy_blowdown_external_validation.json; research\preslhy_blowdown_validation_protocol.json` |
| `preslhy_partb_ambient_external_validation` | **FAIL** | The frozen release model meets the independent ambient Cryostat Part-B pressure-decay screens. | `research\preslhy_partb_ambient_validation.json; research\preslhy_partb_holdout_protocol.json` |
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
- `preslhy_partb_ambient_external_validation`
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
- `preslhy_partb_ambient_external_validation`
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
