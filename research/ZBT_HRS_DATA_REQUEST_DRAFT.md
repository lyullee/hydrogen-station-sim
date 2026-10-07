# Draft data request: ZBT hydrogen test-field HRS logger package

**Do not send without the project owner's review and an approved institutional channel.**

To: Matz Dietrich (`m.dietrich@zbt.de`) / ZBT data custodian; copy the second
corresponding author only if institutionally appropriate
*Representative Hydrogen Sampling at Hydrogen Refuelling Stations: Interplay of
Sampling Strategy and Station Parameters* (DOI
[10.3390/cleantechnol8030091](https://doi.org/10.3390/cleantechnol8030091))

Subject: Metadata crosswalk and untouched logger event for the public Hy-SaM HRS dataset

Dear authors,

I am preparing an academic validation study of a research and training digital
twin for high-pressure gaseous-hydrogen refuelling-station safety. Your 2026
paper describes the ZBT hydrogen test field, including multi-bank storage,
35/70 MPa dispensing, SAE J2601/MC-Formula/PHRYDE operation and logged dispenser
and storage-tank measurements. I have downloaded the CC BY 4.0 Zenodo release
"Group B -- HySam system measurement data" (DOI
[10.5281/zenodo.20590842](https://doi.org/10.5281/zenodo.20590842)) and verified
the three workbook hashes. I am not requesting a duplicate of those files.

The immediate need is a small metadata crosswalk for the released workbooks:

- engineering meaning, units, reference basis and sensor location for `PT01`,
  `PT03`, `PTD10`, `PTD11`, `PTX05`, `TT_D04`, `TT08`--`TT11`, `TT24`,
  `TEX01`, `QT_D02` and `FWg35_Masse`;
- confirmation of whether `QT_D02` is instantaneous hydrogen mass flow and
  `FWg35_Masse` is cumulative transferred mass, including sign and reset rules;
- mapping of `20241023_Test_1_HySaM.xlsx`,
  `20241023_Test_4_HySaM_CESAME.xlsx` and `20241024_Test_9_HySaM.xlsx` to
  article set-up 1 or set-up 2, the 244 L or 77 L Type-IV sink, sampling device
  and test/order identifier;
- event boundaries and identification of purge, aborted-fill, sampling and
  normal refuelling intervals;
- SAE table/protocol, initial pressure, APRR, cooling category and storage-bank
  selection for each released event;
- sensor calibration/uncertainty and known clipping, lag or missing-data notes.

The article supplement was also checked. It provides storage-bank contribution
and composition tables, but no logger dictionary or workbook-to-set-up mapping.
The volume crosswalk is material: replaying the same mass-consistent sessions
with the article's 244 L and 77 L sink geometries produces substantially
different errors, so I will not select a geometry from model fit.

For prospective validation, would you also consider sharing at least one
**disjoint event whose numerical logger outcome has not been supplied or viewed
by this project**? Station, operator and project-sensitive identifiers can be
replaced with pseudonyms. Its minimum useful package is:

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

The new event would be quarantined and hashed on receipt. Inclusion criteria,
preprocessing, model commit and scoring thresholds would be frozen before any
numerical outcomes are inspected. Failed or incomplete events would remain in the
record. The intended use is independent scientific validation, not regulatory
certification or a claim about the ZBT facility.

Please specify the licence or written permission for the new event covering
derived error metrics, plots, repository archiving and journal publication. If
no new event can be released, the channel dictionary and workbook crosswalk
alone would still remove the main ambiguity in the current post-access
diagnostic.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*

## Repository boundary

The public article, Zenodo workbooks and supplement are recorded in
`research/methytrucks_hysam_postaccess_diagnostic_2026_10_08.json` and
`research/methytrucks_supplementary_mapping_recheck_2026_10_08.json`. Existing
rows are post-access diagnostic evidence only. Only a disjoint event protected
by a pre-outcome freeze can become prospective evidence, and it still requires
the station/controller channels defined by the validation protocol.
