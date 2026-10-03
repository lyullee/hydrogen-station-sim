# Draft data request for the NRC British Columbia dispenser study

**Do not send without the project owner's review.**

Subject: Request for de-identified fueling logs underlying NRC Report 56628

Dear NRC authors and data custodian,

I am preparing an academic validation study of a virtual hydrogen-refuelling
station digital twin. The report *Dispenser reliability analysis for hydrogen
refuelling stations in British Columbia* (Report 56628, DOI
<https://doi.org/10.4224/40003368>) analyzes approximately 22,593 H70T40
fueling events at four stations during 2022--2023 and presents pressure,
temperature and flow-pattern classifications.

Could you identify the approved access route or provide a de-identified subset
of the underlying event logs? For independent validation, the most useful
fields are:

- common timestamp or elapsed time and units;
- dispenser/nozzle pressure, vehicle or receptacle pressure, hydrogen
  temperature and mass flow or transferred mass;
- connection pulse, leak-check, fueling, halt/abort and shutdown markers;
- vehicle tank capacity/type, initial state, protocol version and target SOC;
- station storage availability, pre-cooling state, fault category and quality
  flags.

Station and vehicle identities can be replaced with study-specific identifiers.
Please state the licence or written reuse terms, including whether derived
error metrics and anonymised figures may be published in an open repository
and journal article.

If synchronized traces cannot be released, an event-level table plus the data
dictionary and protocol version would still support a bounded operating-range
and fault-taxonomy analysis. We will not treat aggregate figures as numerical
time-series validation. Any received files would be quarantined and hashed
before outcomes are inspected, and eligibility and scoring would be frozen in
advance.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
