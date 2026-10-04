# Draft data request to the SunHydro / DOE Hydrogen Secure Data Center custodian

**Do not send without the project owner’s review.**

To: SunHydro / Proton OnSite and U.S. DOE/NREL Hydrogen Secure Data Center data custodian

Subject: Request for de-identified SunHydro hydrogen-station operating traces for independent validation

Dear data custodian,

I am preparing an independent validation study of a safety digital twin for hydrogen refuelling stations. The DOE project reports describe SunHydro station data acquisition and export to the Hydrogen Secure Data Center, including station production, storage, compression, dispensing, maintenance and safety records. The public reports establish the provenance of the data programme but do not expose the synchronized logger files.

Could you provide a de-identified station-by-fill export, or identify the approved custodian and access route, for an untouched validation subset? The minimum useful fields are:

- a common timestamp or elapsed time and sampling interval;
- vehicle/receptacle and dispenser pressure;
- vehicle/tank, delivered-gas and ambient temperature;
- instantaneous mass flow or cumulative transferred mass;
- initial pressure/SOC, tank capacity/type and protocol or pressure-ramp settings;
- storage-bank, compressor, precooler, valve and dispenser states;
- stop/abort/fault, maintenance, calibration and quality flags.

Station, vehicle and operator identities may be removed. A de-identified CSV, Parquet or Excel export is sufficient. Please state the licence or written reuse and citation terms, including whether derived error metrics and figures may be published in an open repository and journal article. If only aggregate or quarterly reports are available, we will use them only for operating-range context and will not treat them as primary synchronized time-series validation.

Any received files will be quarantined and cryptographically hashed before numerical outcomes are inspected. The eligibility criteria, model commit and scoring protocol will be frozen before evaluation.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
