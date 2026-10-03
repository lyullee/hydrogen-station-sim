# IJHE submission readiness

Target journal: *International Journal of Hydrogen Energy*
Working title: **External validation and evidence-gated decision support for a virtual hydrogen refuelling station digital twin**

## Current decision

**Not ready for submission.** The manuscript can support a bounded tank-model validation claim, a negative full-loop validation result, and a HyRAM+ adapter-verification claim. It cannot yet support an effectiveness or safety claim for SAGA decision support. The goal must remain open until the mandatory items below are complete and the resulting evidence supports the final claims.

The current official IJHE Guide for Authors was checked on 3 October 2026. A research paper should normally remain within 8,000 words and 12 diagrams; the abstract is limited to 150 words; no more than six keywords are allowed; and a separate Highlights file is mandatory with 3–5 bullets of at most 85 characters each. The guide recommends `elsarticle.cls`, requires CRediT roles and a competing-interest statement, and requires a generative-AI disclosure when such tools assist manuscript preparation. Since 1 July 2025, every listed author must provide a valid institutional email address. Source: <https://www.sciencedirect.com/journal/international-journal-of-hydrogen-energy/publish/guide-for-authors>.

## Evidence gate

| Gate | Status | Evidence / required action |
|---|---|---|
| Type-IV tank external validation | Complete for measured boundaries | 12 frozen validation fills; pressure 3.905 MPa, temperature 4.694 °C, SOC 3.812 %p mean RMSE |
| Full station closed-loop validation | Failed | 0/8 development, 0/11 internal-comparison and 0/8 prospectively frozen MC Default holdout fills met all project screens; external holdout mean RMSE 15.862 MPa, 13.230 °C and 18.082 SOC %p |
| HyRAM+ production adapter | Verified within stated scope | Exact v6.1 source identity, 47 upstream tests/803 subtests, three production parity cases |
| Outdoor free-jet display geometry | Complete within bounded scope | Three applicable public experimental families (4 vol% dilution length, distance-dependent heat flux, unconfined overpressure); exact HyRAM+ source and adapter parity; separate radial/directional browser mapping. This is not site-specific validation or a safety-distance claim |
| HIAD casebook leakage review | Pending | Advisory pre-screen flags 16 HIGH, 6 MEDIUM and 2 LOW among 24 holdout vignettes; a qualified non-rating coordinator must inspect every case, rewrite/remove hindsight actions without adding facts, then approve and freeze the complete set |
| Human-participant ethics determination | Pending | Record institutional approval, exemption or not-required determination before reviewer recruitment/rating |
| Blinded SAGA expert review | Pending and mandatory | Three independent qualified reviewers; lock ratings before unmasking |
| SAGA ablation result | Pending | Alarm-only vs direct LLM vs standards-RAG, with unsafe advice, omissions, latency, failures and agreement |
| HIAD design sensitivity | Complete before outcome collection | With 24 events, simulated Wilcoxon power is 77.7% at standardized paired effect 0.6 and 95.7% at 0.8; with zero unsafe events the exact two-sided 95% event-rate upper bound remains 14.2% |
| New untouched full-loop set | Required after redesign for a broad control claim | The prospectively frozen MC Default set failed 0/8 and is now consumed evaluation evidence; redesign without tuning to these outcomes, then freeze and acquire a different external set |
| Author metadata | Pending | Names, affiliations, corresponding author, ORCID |
| Declarations | Pending | CRediT, funding, conflicts and acknowledgements; working AI-use disclosure is included |
| IJHE length and front matter | Conforming draft | 150-word abstract, six keywords, five Highlights under 85 characters; final word/figure count still required |
| LaTeX template and compilation | Pending | Source is structurally checked, but the built-in Windows compiler returned `Unable to find standard directories for platform`; compile with the current Elsevier template before submission |

## Submission package already prepared

- `ijhe_manuscript_draft.tex`: English working manuscript with explicit claim limits.
- `Highlights.txt`: five concise highlights, each under the IJHE 85-character limit.
- `figures/tank_parity.png`: measured/predicted pressure and temperature.
- `figures/tank_case_rmse.png`: case-level validation errors.
- `graphical_abstract.svg` and `.png`: editable and 1328 × 531 px graphical abstract.
- `../output/pdf/IJHE_graphical_abstract.pdf`: visually verified 13 cm submission PDF.
- Reproduction and evidence files in `docs/` and `research/`.
- `research/HIAD_EXPERT_STUDY_PREREGISTRATION.md`: confirmatory comparison,
  endpoints, exclusions, missingness and analysis frozen before holdout collection.
- `research/ETHICS_DETERMINATION_REQUEST.md`, reviewer information sheet and
  data-management plan: institution-ready governance packet; determination pending.
- `research/hiad_study_protocol_manifest.json`: SHA-256 manifest that keeps
  recruitment and holdout collection disabled while governance fields are pending.
- `research/HIAD_DESIGN_SENSITIVITY.md`: pre-outcome power sensitivity and the
  exact zero-event upper bound for the fixed 24-event holdout.
- `research/CONSEQUENCE_GEOMETRY_VALIDATION.md`: public experiment to HyRAM+
  to production adapter to browser-geometry traceability, with explicit site-
  specific and safety-distance exclusions.
- `research/mc_default_external_holdout_protocol.json` and
  `data/public_validation/results/closed_loop_external_holdout/`: prospectively
  frozen protocol plus the retained 0/8 external result and case-level metrics.
- `IJHE_READINESS_AUDIT.md` and `ijhe_readiness_audit.json`: machine-generated
  claim-to-evidence gates; goal completion remains prohibited while any full-
  objective gate is not PASS.

## Finalization sequence

1. Have a non-rating coordinator remove hindsight-action leakage from the 24 holdout HIAD vignettes and freeze the approved casebook.
2. Obtain and record the applicable institutional ethics determination for the expert-review study.
3. Collect all three response variants under frozen provider/model, prompt, sampling and token settings.
4. Build isolated reviewer packets and obtain independent blinded ratings from three qualified hydrogen/process-safety reviewers.
5. Lock the rating database, unmask once, and run the committed analysis script.
6. Add the SAGA effect sizes, bootstrap confidence intervals, unsafe-advice and omission rates, latency, failures and inter-rater agreement to the Results and Abstract.
7. Limit the current process claim to the measured-boundary tank submodel, or redesign the closed-loop protocol using development evidence and evaluate it once on a different, prospectively frozen external dataset. The MC Default outcomes may not be used for tuning.
8. Confirm every author and declaration, regenerate all evidence from the release commit, archive the package with a DOI, and complete a final claim-to-evidence audit.

## Claim language that must remain

- “Measured-boundary tank-model validation,” not “full-station validation.”
- “Public experimental validation inherited through exact HyRAM+ source plus local adapter parity,” not “a new independent field validation.”
- “Directional 4 vol% centreline distance,” not “spherical safety distance.”
- “Research and training prototype,” not “certified controller or autonomous emergency system.”
