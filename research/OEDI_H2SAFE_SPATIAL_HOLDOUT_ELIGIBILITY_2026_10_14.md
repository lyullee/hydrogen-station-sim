# OEDI H2SAFE spatial-holdout eligibility

The OEDI/NLR catalog was opened only after commit `2aa686d` froze the dataset-
specific protocol. The official record identifies DOI `10.7799/17118570`, a
CC BY 4.0 licence, one Lab-1 experiment and four Lab-2 experiments with sensor
coordinates and concentration time series.

The source fails the frozen holdout requirements before numerical scoring:

- the test gas is helium surrogate rather than actual hydrogen;
- five experiments are available rather than the required minimum of 18; and
- the DOI exactly matches the legacy H2SAFE cohort used during candidate
  development, so the source is not an independent holdout.

No archive was downloaded, no numerical sensor response was opened, no model
was run and no parameter was fitted. The detector-transfer gate remains failed
and runtime spatial routing remains disabled.

The new catalog publication is still useful: it establishes a public licence,
official dataset identity, coordinate/time-series availability and a stable
provenance route for the existing helium development evidence. It does not add
actual-hydrogen validation.
