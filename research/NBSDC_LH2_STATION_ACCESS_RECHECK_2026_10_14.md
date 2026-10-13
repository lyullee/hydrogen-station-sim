# NBSDC liquid-hydrogen station dataset access recheck

This recheck records whether a newly identified public catalog candidate can be
used as an independent numerical validation cohort. It intentionally does not
download or copy operational rows.

- Catalog: [NBSDC dataset record](https://nbsdc.cn/general/dataDetail?id=67d50e37195d260905af9869&type=1)
- Dataset identifier: `67d50e37195d260905af9869`
- Dataset description: 16-hour, one-second operational measurements covering a
  35 MPa dispenser, 90 MPa compressor, high-pressure storage banks, and a liquid
  hydrogen pump/tank system.
- Catalog inventory: 7 files, including six operational workbooks/CSV files and
  one description document.

The unauthenticated catalog API exposes the file names and sizes. The raw-file
endpoint returns an application-required response for the first operational
file. No operational rows were downloaded, opened, or copied into the
repository. The machine-readable record is
`research/nbsdc_lh2_station_access_recheck_2026_10_14.json`, and the check can
be reproduced with:

```powershell
.venv\Scripts\python.exe scripts\audit_nbsdc_lh2_station_access.py
```

## Decision

This is an `ACCESS_BOUNDARY_ONLY` result. The candidate is not an independent
validation cohort yet, and it does not change any gate, runtime parameter, or
the 91.7% scope-adjusted closure. A custodian-approved raw-file release and
reuse conditions are required. Once those are available, a pre-access protocol
must be frozen before numerical rows are inspected.
