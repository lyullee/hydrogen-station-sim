# Data request draft: 35/70 MPa dispenser experiment

**Do not send without the project owner's review.**

To: Authors of “Study on comprehensive evaluation of 35 MPa/70 MPa hydrogen
dispenser refueling performance”

Subject: Request for synchronized raw pressure/temperature/flow traces for
independent HRS digital-twin validation

The public article (DOI [10.19799/j.cnki.2095-4239.2020.0049](https://doi.org/10.19799/j.cnki.2095-4239.2020.0049))
reports real 35 MPa and 70 MPa dispenser tests and provides endpoint-table CSV
downloads. For an independent validation study, please advise whether the
underlying time-series records can be shared under a suitable data-use or
publication agreement.

Requested fields, where releasable:

- common timestamp or elapsed time and units;
- vehicle/receptacle pressure and tank temperature;
- dispenser pressure, delivery temperature and mass flow;
- initial conditions, tank volume/type, source pressure and source temperature;
- leak-test pauses, pressure-stage switches, protocol/SAE J2601 settings and stop reason;
- sensor calibration/uncertainty, quality flags and any filtering;
- permission to publish derived error metrics and anonymized plots.

The endpoint values already exposed by the article will be treated as context only.
Any received files will be hashed and quarantined before outcomes are inspected;
the model and scoring protocol will be frozen before evaluation, and all failures
will be retained. No raw file will be redistributed without explicit permission.
