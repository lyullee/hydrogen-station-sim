# OEDI H2SAFE prospective spatial holdout

The public OEDI search result identifies a newly available H2SAFE controlled-gas
release archive with concentration time series, three-dimensional sensor and
source coordinates, geometry and HVAC documentation. No landing-page file
inventory, coordinate values, numerical time series, plots or outcome metrics
were opened before this protocol was prepared.

The existing `pooled_spatial_rank_v1` implementation and its four screens are
locked without modification. At least 18 non-overlapping actual-hydrogen cases
with a common coordinate frame and at least eight usable sensors per case are
required. Every eligible case is included, and no case may be removed after its
responses are viewed. Surrogate, blended, CFD-only, overlapping or incomplete
cases are excluded by the rules fixed in the JSON companion.

The first Git commit containing the JSON protocol is the authoritative freeze.
After that commit, source identity, licence, file hashes and schema eligibility
may be inspected. If any eligibility requirement fails, the model is not run.
If the model is run, every frozen screen must pass and every failure remains in
the record.

This holdout concerns sensor ranking only. It cannot establish concentration
accuracy, alarm timing, detector coverage completeness, ESD performance,
outdoor station dispersion, safety distance or field safety.

