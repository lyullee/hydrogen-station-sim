# CIP 35/70 MPa HRS data boundary recheck

The article-linked `T1.csv.zip` through `T4.csv.zip` files were downloaded into a quarantined directory only after the metadata intake gate passed. The ZIP bytes were hashed before any member was opened. The initial manifest and eligibility report are retained in `research/external_hrs_intake/cip_2020_35_70mpa/manifest.json` and `research/external_hrs_intake/cip_2020_35_70mpa/eligibility.json`.

After the prospective intake decision, the four members were extracted and inspected. Each member contains three rows: an HTML-like header row and a small initial/final-condition summary. None contains an elapsed-time column or synchronized vehicle pressure, temperature and mass-flow channels. The source therefore fails the frozen trace-quality channel contract as `INELIGIBLE_TRACE_CHANNELS` and cannot be used as a station-to-vehicle full-loop holdout.

The files remain quarantined outside the Git repository. Their byte hashes and the exact boundary decision are recorded in `research/cip_2020_35_70mpa_data_boundary_2026_10_05.json`. The article and its summary tables remain useful for operating-range context and a request to the data custodian, but no calibration, tuning or IJHE physical-validation claim is made from them.
