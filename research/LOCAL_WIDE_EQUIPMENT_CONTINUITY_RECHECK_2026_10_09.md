# Local wide equipment continuity recheck (2026-10-09)

An in-memory scan of the owner-managed wide equipment logs found **8 wide
files and 653,442 data rows**. The time axis parsed without failures or
negative intervals; the median positive interval was **1 s** and the maximum
observed gap was **3 s**. The screen counted **3,873 transitions** in generic
state-like fields. These results strengthen the conclusion that the local
collection contains usable station-equipment dynamics rather than static
design values.

This artifact deliberately does not publish source paths, filenames, headers,
tags, calendar dates, raw values, or per-file metrics. State-like fields are
only structural candidates. Their engineering meanings, pressure reference,
units, alarm semantics, and reset behavior still require custodian
attestation. The result is therefore eligible for continuity and missingness
checks, but it is **not** independent external validation, a runtime
calibration, a vehicle-fill validation, or a consequence-distance result.

The machine-readable aggregate is
[`local_wide_equipment_continuity_recheck_2026_10_09.json`](local_wide_equipment_continuity_recheck_2026_10_09.json).
