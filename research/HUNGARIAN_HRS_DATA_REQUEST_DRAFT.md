# Public-data request draft: Hungarian HRS digital-twin validation

Reference: Hasulyó, *Dynamic Digital Twin Network for Real-Time Safety
Monitoring and Predictive Risk Assessment of Hydrogen Refueling
Infrastructure*, DOI
[10.32604/ee.2026.081099](https://doi.org/10.32604/ee.2026.081099).

The article reports validation against operational data from an existing
Hungarian HRS and explicitly states that supporting data are unavailable for
consent and legal reasons. This draft requests only a de-identified release or
an approved secure-analysis arrangement; it does not assume that publication
of the article grants access to the measurements.

Please advise whether a reproducible subset can be shared under an approved
data-use agreement. The minimum fields needed for an independent holdout are:

- synchronized timestamps and sampling interval;
- vehicle or receptacle pressure and temperature;
- dispenser pressure, delivery temperature and mass flow or transferred mass;
- compressor, buffer-storage and precooler operating states where recorded;
- initial conditions, tank capacity, fill target and protocol category;
- sensor accuracy, quality flags, missing-data convention and event boundaries;
- a permission statement covering derived metrics, plots and public hashes.

The files would be hash-locked before model output is inspected and used only
for a pre-registered validation holdout. No restricted raw data would be
committed or redistributed. All failed cases would remain reported.
