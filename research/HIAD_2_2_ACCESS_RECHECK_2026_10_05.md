# HIAD 2.2 access and station-incident recheck

- Generated: 2026-10-05T02:50:33.529268+00:00
- Source: [European Hydrogen Incidents and Accidents Database HIAD 2.2](https://minerva.jrc.ec.europa.eu/en/shorturl/capri/hiadpt)
- Local acquisition SHA-256: 295772b60a4afe5ef47a00bc314eed48b76c170be00c29952d60e50fedd6f55f
- Workbook rows: EVENTS 1142, FACILITY 1142, CONSEQUENCES 1142, EVENT NATURE 1142, LESSONS LEARNT 1142
- Hydrogen refuelling station records: **34**
- Existing HIAD casebook candidate: **24** cases; coordinator review remains pending

## Evidence use

HIAD 2.2 is used here as public actual-incident evidence for scenario taxonomy, response grounding and a future blinded SAGA casebook. The JRC page requires the specified acknowledgement and preserves uncertainty inherited from each original source.

The workbook does not contain a synchronized station-to-vehicle pressure/temperature/mass-flow logger archive. These records therefore do not close the numerical full-loop validation gate and are not represented as such.

## Reproducible acquisition

1. Download the official workbook from the source page/download URL.
2. Compute SHA-256 and compare it with the JSON artifact.
3. Run scripts/build_hiad_2_2_access_recheck.py.
4. Retain the source workbook locally; do not alter the indexed event fields.

## Next controlled step

A non-rating coordinator must review and mask hindsight response/lesson leakage before any casebook freeze. Ethics determination and independent expert review remain prerequisites for the SAGA effectiveness gate.
