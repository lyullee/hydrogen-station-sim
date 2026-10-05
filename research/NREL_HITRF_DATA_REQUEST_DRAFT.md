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

The public DOE/NLR high-flow presentations provide additional case identifiers
that would make a release easy to map without exposing station identity: the
December 2022 H2IQ slides report 61.5 kg and 82.3 kg HDVS demonstrations with
pressure, temperature and mass-flow plots, and the March 2024 H2IQ materials
report a 73 kg SAE J2601-5 test (423.5 s total, 358.9 s fueling, 172.3 g/s
average and 483.33 g/s peak). The slides are chart-only public evidence, so I
am requesting the underlying synchronized logger export rather than treating
the plotted curves as raw validation data.

Public references for these leads:

- https://www.energy.gov/sites/default/files/2022-12/h2iq-121922.pdf
- https://www.energy.gov/sites/default/files/2024-04/h2iqhour-03262024.pdf
- https://www.energy.gov/cmei/fuels/march-h2iq-hour-hydrogen-fuel-dispensing-medium-and-heavy-duty-vehicles-text-version

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
