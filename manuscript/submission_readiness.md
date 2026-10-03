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
| Full station closed-loop validation | Failed | 0/8 development and 0/11 internal-comparison fills met all project screens; report as a negative result |
| HyRAM+ production adapter | Verified within stated scope | Exact v6.1 source identity, 47 upstream tests/803 subtests, three production parity cases |
| Outdoor station plume geometry | Not independently validated | The open-channel experiment is not geometrically applicable to the outdoor free jet |
| HIAD casebook leakage review | Pending | Advisory pre-screen flags 16 HIGH, 6 MEDIUM and 2 LOW among 24 holdout vignettes; a qualified non-rating coordinator must inspect every case, rewrite/remove hindsight actions without adding facts, then approve and freeze the complete set |
| Human-participant ethics determination | Pending | Record institutional approval, exemption or not-required determination before reviewer recruitment/rating |
| Blinded SAGA expert review | Pending and mandatory | At least two independent qualified reviewers; lock ratings before unmasking |
| SAGA ablation result | Pending | Alarm-only vs direct LLM vs standards-RAG, with unsafe advice, omissions, latency, failures and agreement |
| New untouched full-loop set | Recommended for a broad control claim | Freeze the next protocol representation before collecting or obtaining new cases |
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

## Finalization sequence

1. Have a non-rating coordinator remove hindsight-action leakage from the 24 holdout HIAD vignettes and freeze the approved casebook.
2. Obtain and record the applicable institutional ethics determination for the expert-review study.
3. Collect all three response variants under frozen provider/model, prompt, sampling and token settings.
4. Build isolated reviewer packets and obtain independent blinded ratings from at least two qualified hydrogen/process-safety reviewers.
5. Lock the rating database, unmask once, and run the committed analysis script.
6. Add the SAGA effect sizes, bootstrap confidence intervals, unsafe-advice and omission rates, latency, failures and inter-rater agreement to the Results and Abstract.
7. Decide whether the paper limits the process claim to the tank submodel or adds a new untouched full-loop dataset.
8. Confirm every author and declaration, regenerate all evidence from the release commit, archive the package with a DOI, and complete a final claim-to-evidence audit.

## Claim language that must remain

- “Measured-boundary tank-model validation,” not “full-station validation.”
- “Adapter parity with the installed HyRAM+ API,” not “independent HyRAM physics validation.”
- “Directional 4 vol% centreline distance,” not “spherical safety distance.”
- “Research and training prototype,” not “certified controller or autonomous emergency system.”
