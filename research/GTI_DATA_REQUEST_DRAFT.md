# Draft data request to the GTI / DOE hydrogen-station performance data custodian

**Do not send without the project owner's review.**

To: Gas Technology Institute / U.S. DOE EERE data custodian for DOI
10.2172/1824631

Subject: Request for de-identified hydrogen-station fueling logger traces for
independent validation

Dear data custodian,

I am preparing an independent validation study of a safety digital twin for
hydrogen refuelling stations. The public *Hydrogen Station Performance
Evaluation (Final Report)* (DOI 10.2172/1824631) describes a custom
data-acquisition campaign deployed at five California stations over roughly
four years. The report identifies vehicle pressure and temperature, mass
dispensed, compressor flow, storage pressure, station temperatures, fill mode
and maintenance fields, but the public record does not include the
synchronized logger export.

Could you provide a de-identified station-by-fill export, or identify the
approved custodian and access route, for a small untouched holdout? The minimum
useful fields are:

- a common timestamp or elapsed time and sampling interval;
- vehicle or receptacle pressure, station/dispenser pressure and gas flow;
- vehicle, hose/dispenser and delivered-gas temperature;
- instantaneous mass flow and/or cumulative transferred mass;
- initial pressure/SOC, tank capacity/type and ambient conditions;
- cascade-bank, compressor, precooler, valve and protocol-mode states;
- stop/abort/fault markers, sensor units, calibration/uncertainty and quality flags.

Station, vehicle and operator identities may be removed. Please state the
licence or written reuse and citation terms, including whether derived error
metrics and figures may be published in an open repository and in a journal
article. If only event-level summaries are available, we will use them for
operating-range context and will not treat them as primary synchronized
time-series validation.

Any received files will be quarantined and cryptographically hashed before
outcomes are inspected. The eligibility criteria, model commit and scoring
protocol will be frozen before evaluation.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
