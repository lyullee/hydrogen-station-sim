# Draft data request to the 35/70 MPa dispenser-test authors

**Do not send without the project owner's review.**

To: Corresponding author of DOI 10.19799/j.cnki.2095-4239.2020.0049

Subject: Request for de-identified synchronized 35/70 MPa hydrogen dispenser test traces

Dear authors,

I am preparing an independent validation study of a hydrogen-refuelling-station
safety digital twin. Your paper, *Study on comprehensive evaluation of 35 MPa/70
MPa hydrogen dispenser refueling performance* (DOI
10.19799/j.cnki.2095-4239.2020.0049), reports real-station 35 MPa and 70 MPa
vehicle fills and describes pressure, temperature and mass-flow recordings. The
public page exposes initial/final summary tables, but not the common-time-base
logger traces behind the plotted curves.

Would you be able to share a de-identified export of the original test records,
or identify the approved data custodian and access route? The minimum useful
fields are:

- elapsed time or synchronized timestamp and sampling interval;
- vehicle/receptacle pressure and dispenser/source pressure;
- vehicle/tank, dispenser/inlet and ambient temperature;
- instantaneous mass flow and/or cumulative transferred mass;
- initial conditions, tank type/volume, gas-source pressure and temperature;
- leak-check, pressure-ramp, storage-bank switching and stop-event markers;
- sensor units, calibration/uncertainty information and quality/exclusion flags.

Station, vehicle and operator identities can be removed. Please state the
licence or written reuse and citation terms, including whether derived error
metrics and figures may be published in an open repository and a journal
article. If the full trace cannot be shared, an event-level table plus a data
dictionary would still support a separate operating-range benchmark, but it
would not be treated as primary time-series validation.

Any received files would be quarantined and cryptographically hashed before
model outcomes are inspected. The eligibility criteria, protocol and model
commit would be frozen before evaluation.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
