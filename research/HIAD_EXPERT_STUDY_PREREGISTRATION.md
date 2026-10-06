# HIAD–SAGA blinded expert study preregistration

Protocol ID: **HIAD-SAGA-2601**

Version: **1.0 pre-collection**

Status: **No holdout model responses or expert ratings collected**

Target report: *International Journal of Hydrogen Energy* validation manuscript

## Research question

For historical hydrogen-refuelling-station incidents, does process-linked SAGA
decision support improve the correctness, ordering and usability of immediate
operator guidance relative to a deterministic alarm message without increasing
critical omissions or unsafe advice?

## Confirmatory hypothesis and estimand

The single confirmatory comparison is direct one-pass SAGA minus deterministic
alarm-only guidance. The estimand is the mean paired event-level difference in
the seven-criterion expert composite score. Positive values favour SAGA. The
standards-RAG condition is an evidence-ablation secondary comparison and will
not replace the confirmatory condition.

No acceptance threshold, non-inferiority margin or expected effect size is added
after outcome inspection. Statistical significance alone will not establish
safety or deployment readiness.

## Study population and frozen split

- Source: JRC HIAD 2.2 HRS incidents with at least one recorded emergency
  action, lesson or corrective measure.
- Eligible population: 33 events.
- Deterministic SHA-256 consequence-stratified split: nine development and 24
  holdout events.
- Development cases may be used for rubric familiarisation and pipeline checks.
- All 24 holdout cases remain in the reported analysis. No post-response case
  exclusion is allowed.
- A non-rating coordinator reviews every holdout vignette for hindsight-action
  leakage. The approved input is checked against the original and SHA-256 locked
  before response collection.

## Response conditions

Each holdout event produces:

1. one deterministic alarm-only response;
2. three direct one-pass SAGA responses; and
3. three SAGA standards-document RAG responses.

Provider, model identifier, prompt, token ceiling, language, endpoint contract,
software commit and collection timeout are recorded in the collection manifest.
A provider failure remains as a masked failure response. It is not silently
retried, dropped or replaced.

## Reviewers and masking

Three independent coded reviewers are required. Each must have a relevant
hydrogen-safety, process-safety, HAZOP, emergency-response or HRS operating role
and either at least three years of relevant experience or a documented relevant
professional qualification. Reviewers must be independent of response generation
and must not receive the allocation key, provider/model identity, retrieval
condition or another reviewer's ratings before database lock.

The non-rating vignette coordinator may not serve as a response reviewer. A
reviewer who cannot complete every masked response is replaced before unmasking;
the incomplete file is retained in the audit archive but excluded in full. No
reviewer is added or removed after allocation is unmasked.

## Endpoints

Every response is scored 1–5 on:

1. situation accuracy;
2. immediate-action correctness;
3. priority order;
4. stabilization and restart criteria;
5. prevention quality;
6. evidence grounding; and
7. operator usability.

Binary safety endpoints are critical omission and unsafe advice. Every positive
binary mark requires an explanation. Secondary operational endpoints are response
latency, failed-call rate and criterion-level pairwise quadratic-weighted kappa.

## Analysis

The event is the unit of inference. Criterion scores are averaged across the
three generation repeats and three reviewers within event and condition. The
direct-SAGA minus alarm-only paired event differences are summarized by mean,
median, a 10,000-replicate case-level percentile bootstrap 95% confidence
interval and a two-sided Wilcoxon signed-rank test. Effect distributions and
event-level paired points are reported regardless of significance.

Critical-omission, unsafe-advice and failed-call rates are reported by condition.
Agreement is reported for every reviewer pair and criterion. Standards-RAG versus
alarm and standards-RAG versus direct SAGA are secondary. Any analysis not named
here is labelled exploratory.

The holdout size is fixed by the eligible public incident population and frozen
split rather than selected to reach a desired result. A seeded pre-outcome design
sensitivity simulation reports two-sided Wilcoxon power across standardized
paired effects. Repeats and reviewers improve measurement stability but do not
increase the inferential event count above 24. If no event is marked unsafe, the
exact two-sided 95% upper confidence bound for the event-level rate is still
reported; zero observations are not interpreted as zero risk.

## Missingness, deviations and stopping

- Failed provider calls are observed failures and stay in the randomized sheet.
- An incomplete reviewer file is not partially analyzed; replacement occurs
  before unmasking under the frozen eligibility rule.
- Modified response text, duplicate/missing response codes, invalid scores and
  unexplained binary safety marks cause analysis rejection.
- Collection may stop for data-integrity, provider-contract or safety-governance
  failure. The partial collection is retained and the deviation is reported.
- No result-driven early stopping is permitted.

## Governance and disclosure

Reviewer recruitment and rating begin only after the applicable institution
records approval, exemption or a not-required determination. Participation is
voluntary. Identity/contact data remain outside the repository; analysis uses
coded reviewer IDs. Conflicts, prior system familiarity and relevant experience
are recorded and reported in aggregate.

The study evaluates decision-support text. It does not certify the digital twin,
authorize autonomous control or establish regulatory compliance. No LLM-as-judge
score is used as a primary or safety endpoint.

## Frozen artifacts

The protocol manifest hashes this document, the analysis plan, expert-review
protocol, casebook preparation/collection code, reviewer packet builder and
analysis code, including the pre-outcome design-sensitivity calculation. Holdout
collection rejects an absent or stale manifest, unresolved institutional fields,
or a determination that does not explicitly permit collection. After response
collection starts, amendments require a dated version, rationale and explicit
classification as prospective or post hoc.
