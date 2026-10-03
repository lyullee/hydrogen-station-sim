# Draft data request to the NRC/HTEC hydrogen-station leakage-data custodian

**Do not send without the project owner's review.**

To: National Research Council Canada / HTEC data custodian

Subject: Request for de-identified operational HRS streams for independent leak and safety-digital-twin validation

Dear data custodian,

I am preparing an academic validation study of a hydrogen-refuelling-station
safety digital twin and evidence-grounded decision-support assistant. The
Government of Canada DTPR AI Register describes your operational leakage
detection system as using anonymized HTEC station streams for hydrogen
production, hydrogen filling and station operating modes.

Could you provide a de-identified extract, or identify the approved access
route, for an independent evaluation split? The minimum useful fields are:

- common timestamp or elapsed time, time zone and engineering units;
- station and subsystem identifier, operating mode and fill start/stop markers;
- produced mass, dispensed/filled mass, pressure, temperature and mass-flow
  channels for the relevant compressor, storage, dispenser and vehicle-side
  interfaces;
- gas-detector channels, alarm/event labels, maintenance windows and known
  leak or loss intervals where available;
- sensor range, quality flags, calibration/uncertainty metadata and data
  dictionary.

Station identity and customer information are not required. A de-identified
CSV, Parquet or Excel export is sufficient. Please state the licence or written
reuse terms, including whether derived loss metrics, validation figures and
anonymized event summaries may be published in an open repository and journal
article.

The requested use is independent evaluation, not model fitting. Any received
files would be quarantined, cryptographically hashed and checked for
provenance before outcomes are inspected. Model version, eligibility criteria
and scoring thresholds would be frozen before evaluation, and any synthetic
fault injection would remain explicitly separate from real event evidence.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
