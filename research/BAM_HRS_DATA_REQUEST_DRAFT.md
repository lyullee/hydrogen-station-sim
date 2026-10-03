# Draft data request to the BAM demonstration hydrogen refuelling station study

**Do not send without the project owner's review.**

To: Corresponding author and BAM demonstration-HRS data custodian

Subject: Request for de-identified HRS sensor traces for independent safety-digital-twin validation

Dear authors,

I am preparing an academic validation study of a hydrogen-refuelling-station
safety digital twin and evidence-grounded decision-support assistant. I read
your paper, *Data-Driven Intelligent Analysis System for Monitoring and Anomaly
Detection in Hydrogen Refueling Station* (DOI
10.3390/app16157856), which reports field deployment at the BAM demonstration
station with compressor, storage and dispenser safety sensors.

Could you provide a de-identified extract, or identify the approved custodian
and access route, for an independent validation split? The minimum useful
fields are:

- a common timestamp or elapsed time and units;
- sensor tag, location, engineering unit, range and calibration/quality flags;
- compressor inlet/outlet pressure, storage-bank pressure, dispenser
  temperature and dispenser flow channels;
- operating mode, fueling start/stop markers, protocol/temperature category,
  and maintenance or fault annotations where available;
- any vehicle or receptacle pressure, tank temperature, transferred mass and
  initial conditions recorded during fills.

Station and operator identities are not required. A de-identified CSV, Parquet
or Excel export with a data dictionary is sufficient. Please state the licence
or written reuse and citation terms, including whether derived error metrics,
figures and anonymized event summaries may be published in an open repository
and journal article.

The requested use is independent evaluation, not model fitting. If the data
contain only normal operation, they can still support sensor-quality and
false-alarm validation; semi-synthetic injections would be retained as a
separate diagnostic and would not be treated as real incident evidence. Any
received files would be quarantined and hashed before outcomes are inspected,
and the model commit and eligibility criteria would be frozen before scoring.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*

