# Public-data request draft: ZBT/MetHyTrucks HRS sampling traces

**Do not send without the project owner's review.**

Reference: Dietrich et al., “Representative Hydrogen Sampling at Hydrogen
Refuelling Stations: Interplay of Sampling Strategy and Station Parameters,”
*Clean Technologies* 8(3), 91 (2026), DOI
[10.3390/cleantechnol8030091](https://doi.org/10.3390/cleantechnol8030091).

The article reports real experiments at the ZBT hydrogen test field, including
35/70 MPa dispensing, a 244 L Type-IV sink, multiple storage banks, and logged
dispenser/tank data. Its data-availability statement says the raw data can be
made available by the authors on request. Please consider sharing a de-identified
machine-readable trace under terms that permit derived metrics and anonymized
plots.

Requested fields, where releasable:

- common timestamp and sampling interval;
- dispenser pressure, delivery temperature and mass flow;
- sink/receptacle pressure and temperature, transferred mass and tank volume/type;
- selected storage-bank pressure/state, pre-cooling setpoint and protocol mode;
- initial/final conditions, leak-test pauses, valve or bank-switch events and stop reason;
- sensor accuracy, quality flags, filtering and missing-data convention;
- permission to publish derived error metrics and anonymized figures.

The trace would be used as an untouched station-to-receptacle holdout. Any
received file would be quarantined and hashed before numerical outcomes are
inspected; the model commit and scoring protocol would be frozen first, and all
failed cases would remain reported. Restricted raw files would not be
redistributed without explicit permission.
