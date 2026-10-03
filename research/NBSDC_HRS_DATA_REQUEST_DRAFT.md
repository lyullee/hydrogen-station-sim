# NBSDC HRS operational-data request

## Candidate record

- Dataset: **Operational Data List of Hydrogen Refueling Stations for Beijing Winter Olympics**
- CSTR identifier: `CSTR:16666.11.nbsdc.aI3fJrzX`
- Catalog landing page: <https://cstr.cn/16666.11.nbsdc.aI3fJrzX>
- Catalog record: <https://xiaopeiwang.com/en/result/r-057159df>
- Coverage: 2022
- Authors shown by the catalog: Jin Zhenhua; Wang Xiaopei
- Organization shown by the catalog: Tsinghua University
- Catalog metadata: four files, 10.22 MB
- Declared topics: dispenser monitoring, fueling records, compressor monitoring

The catalog metadata is valuable for candidate selection, but the access policy
currently says **approval required**. A request is therefore required before any
file can be treated as public validation evidence. The no-file response from the
catalog file-tree endpoint must be retained as evidence of the present access
boundary.

## Requested material

Please provide, under terms permitting research use and publication of derived
statistics:

1. The four original files and their SHA-256 digests.
2. A data dictionary for dispenser, fueling-record and compressor-monitoring
   channels, including units, sampling rates, time zone and missing-value codes.
3. Synchronized timestamps for vehicle/receptacle pressure, hydrogen mass flow or
   transferred mass, gas temperature, ambient temperature and storage/compressor
   states, where available.
4. Station topology and equipment metadata sufficient to map source, cascade,
   compressor, precooler and dispenser channels without guessing.
5. Quality flags, maintenance intervals, aborted fills, alarm/ESD events and any
   known sensor recalibration or clock corrections.
6. Permission to publish only de-identified, hashed, derived validation traces
   and case-level metrics in a scientific paper and repository.

## Proposed quarantine and validation procedure

On receipt, the files will be copied to the gitignored raw-data area, hashed
before inspection, and registered in a new protocol manifest. Eligibility and
the holdout split will be frozen before the numerical outcomes are opened. The
locked station model will then be run once; all eligible failures and missing
channels will remain in the report. The files will not be used to tune the
model after the holdout outcome is known.

## Current status

As of 2026-10-03, the catalog exposes metadata but no downloadable file tree
without approval. This candidate is **not** counted in the full-loop validation
gate.
