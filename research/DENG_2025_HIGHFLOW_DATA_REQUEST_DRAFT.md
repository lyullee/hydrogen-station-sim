# Draft data request for the 2025 IJHE high-flow tank experiment

**Do not send without the project owner's review.**

Subject: Request for de-identified high-flow hydrogen refuelling traces for independent validation

Dear authors,

I am preparing an academic validation study of a virtual hydrogen-refuelling
station digital twin. Your article, *Experimental–numerical optimization of
inlet angles for controlling temperature rise during high-flow hydrogen
refueling of large-scale storage tanks* (DOI
<https://doi.org/10.1016/j.ijhydene.2025.151093>), reports time-resolved
mass-flow measurements and tank-temperature responses from a 35 MPa high-flow
platform.

Could you share a de-identified machine-readable subset, or identify the
approved repository or custodian, containing the experimental traces used for
the validation? The minimum useful fields are:

- elapsed time and sampling interval;
- inlet mass flow, inlet pressure and inlet temperature;
- tank pressure and at least one internal or wall temperature channel;
- tank volume, type, geometry/aspect ratio and inlet-angle configuration;
- initial and final state, ambient temperature, pre-cooling condition and
  pressure-ramp or control protocol;
- calibration/quality flags and any excluded intervals.

CSV, XLSX or a repository export is sufficient. Please state the licence or
written reuse terms, including whether derived error metrics, figures and
aggregated traces may be published in an open repository and journal article.
Station and operator identities are not required.

If the full logger export cannot be shared, a limited subset covering one
precooled and one non-precooled run would still be useful. We will quarantine
and hash any received files, freeze the model commit and eligibility criteria
before evaluating them, and will not digitise figures as a substitute for the
underlying time series.

Because the article already reports aggregate temperature errors, the strongest
design would be a custodian-held blind split. If unreported repeats exist,
please retain their case identifiers and numerical outcomes until we send a
timestamped model commit, channel mapping and scoring protocol. A calibration
subset may be released first; the disjoint blind subset can then be released
once for no-fitting evaluation. If no unreported repeats exist, we will label
the received traces as post-publication transfer diagnostics rather than an
untouched validation holdout.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
