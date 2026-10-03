# Draft data request to the JRC GasTeF data custodian

**Do not send without the project owner's review.**

To: European Commission Joint Research Centre, High Pressure Gas Testing
Facility (GasTeF) data custodian

Subject: Request for de-identified GasTeF tank-filling traces for independent model validation

Dear JRC GasTeF team,

I am preparing an academic validation study of a research and training digital
twin for hydrogen refuelling-station safety. Your open-access article,
*JRC reference data from experiments of on-board hydrogen tanks fast filling*
(DOI 10.1016/j.ijhydene.2014.03.227), describes a GasTeF database with more
than 133 filling and emptying entries from commercial high-pressure tanks.

Could you provide a de-identified subset, or identify the approved custodian
and access route, for an independent tank-filling holdout? The minimum useful
fields are:

- common timestamp or elapsed time and units;
- tank pressure and gas-path/inlet pressure;
- internal gas temperature channels and external tank/sleeve temperature;
- inlet temperature and instantaneous mass flow or transferred mass;
- tank type, volume, nominal pressure, initial state and fill endpoint;
- filling protocol or pressure-ramp information, cooling condition and quality
  flags.

Station and operator identities are not required. A de-identified CSV or Excel
export is sufficient. Please state the licence or written reuse and citation
terms, including whether derived error metrics and figures may be published in
an open repository and journal article.

If synchronized traces are unavailable, an event-level table with measurement
definitions and a data dictionary would still support a separate field-realism
analysis. We will not treat aggregate plots or digitised figures as primary
time-series validation. Any received files would be quarantined and hashed
before outcomes are inspected, and the model commit and eligibility criteria
would be frozen before evaluation.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
