# HIAD 2.2 public HRS evidence inventory

This record is generated from the European Commission Joint Research Centre's
public HIAD 2.2 workbook. It is an incident and near-miss evidence inventory,
not a coordinator-approved blinded casebook and not a time-series physics
validation set.

## Reproducible extraction

```text
.venv\Scripts\python.exe scripts/summarize_hiad_hrs_evidence.py
```

The current output is stored in
`research/hiad_hrs_public_evidence.json`. The extractor joins the workbook's
`EVENTS`, `FACILITY`, `LESSONS LEARNT`, `EVENT NATURE`, and `REFERENCES` sheets
and selects rows whose `FACILITY.Application` is exactly
`Hydrogen refuelling station`. Event identifiers and source links are retained;
response and lesson text is excluded from the compact output so that the file
cannot be passed to a blinded assistant as a leaked answer key.

## Current public evidence

The source contains **34 HRS rows**. Of these, 29 include an emergency-action
field, 24 include a lesson-learned field, and 25 include corrective measures.
The records cover dispenser leaks and hose failures, compressor faults,
storage leaks/explosions, transfer events, detection failures and operational
near-misses. Exact counts and immutable source digest are in the JSON record.

HIAD 2.2 is free for public use with acknowledgement, but the JRC warns that
the validity of each event depends on the original public or secondary source.
The dataset has no exposure denominator and generally lacks synchronized
pressure, temperature and mass-flow traces. It therefore supports traceable
scenario coverage, response-language grounding and qualitative failure-mode
checks only. It cannot by itself validate station physics, estimate incident
probabilities, or establish a safety distance.

Source: [JRC HIAD 2.2 download and terms](https://minerva.jrc.ec.europa.eu/en/shorturl/capri/hiadpt)

