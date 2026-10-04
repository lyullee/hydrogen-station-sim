# Draft data request: ZBT hydrogen test-field HRS logger package

**Do not send without the project owner's review and an approved institutional channel.**

To: Corresponding author / data custodian for Dietrich et al.,
*Representative Hydrogen Sampling at Hydrogen Refuelling Stations: Interplay of
Sampling Strategy and Station Parameters* (DOI
[10.3390/cleantechnol8030091](https://doi.org/10.3390/cleantechnol8030091))

Subject: Request for a de-identified synchronized HRS logger package for independent validation

Dear authors,

I am preparing an academic validation study of a research and training digital
twin for high-pressure gaseous-hydrogen refuelling-station safety. Your 2026
paper describes the ZBT hydrogen test field in Duisburg, including multi-bank
storage, 35/70 MPa dispensing, SAE J2601/MC-Formula/PHRYDE operation and logged
dispenser and storage-tank measurements.

Would you consider sharing a de-identified, rights-cleared logger export for a
subset of refuelling or sampling events? Station, operator and project-sensitive
identifiers can be replaced with pseudonyms. The minimum useful package is:

- common elapsed time or timestamp, units, sampling interval and time-zone rule;
- source/storage-bank pressure and temperature, bank selection and valve state;
- dispenser/hose pressure, delivery temperature and instantaneous or cumulative
  mass flow;
- sink or vehicle/test-tank pressure, gas or average temperature and transferred
  mass/state of charge;
- protocol name/version, target pressure, initial state, ambient condition and
  pre-cooling category;
- event boundaries, leak-check pauses, controller mode, fault/interlock state and
  data-quality flags;
- sensor calibration/uncertainty information and any known missing or clipped
  intervals.

The files would be quarantined and hashed on receipt. Inclusion criteria,
preprocessing, model commit and scoring thresholds would be frozen before any
numerical outcomes are inspected. Failed or incomplete events would remain in the
record. The intended use is independent scientific validation, not regulatory
certification or a claim about the ZBT facility.

Please also specify the licence or written permission covering derived error
metrics, plots, repository archiving and journal publication. If the complete
logger package cannot be released, a small de-identified subset or a data-access
agreement with the channel dictionary and reuse terms would still be valuable.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*

## Repository boundary

The public article is recorded in
`research/zbt_hrs_sampling_article_data_boundary_2026_10_05.json`. Until a
rights-cleared synchronized export is received and frozen, it remains an
operating-range and station-configuration source only. It must not be used to
tune the production model or reported as a full-loop holdout.
