# Draft data request to Cal State LA Hydrogen Research and Fueling Facility

**Do not send without the project owner's review.**

To: Cal State LA HRFF research/data custodian (for example, the corresponding
authors of DOI 10.1016/j.ijhydene.2023.04.084 and DOI
10.1016/j.jclepro.2021.129737)

Subject: Request for de-identified HRS fill-level traces for independent model validation

Dear Cal State LA Hydrogen Research and Fueling Facility team,

I am preparing an academic validation study of a research and training digital
twin for hydrogen refuelling-station safety. Your open-access study,
*Multi-year energy performance data for an electrolysis-based hydrogen
refueling station* (DOI 10.1016/j.ijhydene.2023.04.084), describes real HRFF
operation from 2016–2020 and more than 4,500 refueling events. The related
back-to-back fueling study (DOI 10.1016/j.jclepro.2021.129737) describes a
one-year event and station behavior dataset; its accepted manuscript is
available from OSTI (record 1977265). I am contacting the data custodian
because the public records do not include synchronized raw traces.

Could you provide a de-identified event-level export, or identify the approved
custodian and access route, for a small independent holdout? The minimum useful
fields are:

- common timestamp or elapsed time and units;
- vehicle/receptacle and station/hose pressure;
- vehicle/tank, hose and delivered-gas temperature;
- instantaneous mass flow or cumulative delivered mass;
- vehicle capacity, initial pressure/SOC, protocol and temperature category;
- storage-bank state, compressor/precooler state and quality/exclusion flags.

Station and operator identities are not required. A de-identified CSV or Excel
export is sufficient. Please state the licence or written reuse and citation
terms, including whether derived error metrics and figures may be published in
an open repository and journal article.

If synchronized fill traces are unavailable, an event-level table with the
measurement definitions and a data dictionary would still be useful for a
separate field-realism analysis. We will not treat aggregate plots or
digitised figures as primary time-series validation. Any received files would
be quarantined and hashed before outcomes are inspected, and the model commit
and eligibility criteria would be frozen before evaluation.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
