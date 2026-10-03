# Draft data request to NREL HITRF / NFCTEC

**Do not send without the project owner's review.**

To: NREL Hydrogen Infrastructure Testing and Research Facility / NFCTEC data
custodian

Subject: Request for de-identified HITRF fueling traces for independent HRS model validation

Dear NREL HITRF/NFCTEC team,

I am preparing an academic validation study of a research digital twin for
hydrogen refueling-station process and safety analysis. NREL's public HITRF and
Hydrogen Fueling Infrastructure materials describe full-station measurement,
validation and composite data products, but the public products do not expose
the synchronized raw fueling traces needed for an independent controller
evaluation.
The HITRF 36 L experiment reported by Kuroki et al. (DOI
10.1002/ente.202300239) is a specific priority lead: it describes a 6.3 to
73.0 MPa fill in 186 seconds with receptacle, internal-gas and liner
temperature measurements, while its public data-availability statement says
that the research data are not shared. If those traces can be released under
an approved de-identification and reuse agreement, please include that case.

Could you provide a small de-identified holdout set, or identify the approved
access route, containing the following fields where releasable?

- common timestamp or elapsed time and units;
- dispenser/receptacle and vehicle pressure;
- delivered-gas, hose and vehicle temperature;
- instantaneous mass flow or cumulative transferred mass;
- vehicle capacity, initial condition, protocol and temperature category;
- storage-bank, compressor and precooler state, including pressure schedules;
- quality flags, aborted fills, maintenance intervals and alarm/ESD states.

Station and operator identities are not required. Please state the licence or
written reuse terms, including whether de-identified traces and derived error
metrics may be published in an open repository and an IJHE submission.

If raw traces cannot be released, an event-level export with a data dictionary
and a contact for the underlying measurements would still be useful. Aggregate
composite data products will be retained as operating-range context and will
not be represented as time-series validation.

Any received files will be quarantined and hashed before outcome inspection;
eligibility, the holdout split and the model commit will be frozen before the
model is run. All eligible failures will be retained.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
