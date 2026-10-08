# WSKBIJ apparatus-metadata audit

Decision: **insufficient public metadata for an apparatus-aware model**.

The audit inspected the complete publisher README and summary workbook plus
HTTP range reads of four raw files spanning both acquisition eras. It did not
download the multi-gigabyte video archive or the complete 5+ GB trace set.

## What the public archive supports

- 51 experiment identifiers with nozzle diameter, reservoir pressure and an
  ignition-position code.
- Four transient overpressure channels (`P01`--`P04`) already stored in kPa at
  500 kHz.
- `PT1`, `PT2` and trigger voltages for both campaigns.
- Mass-flow voltage for experiments 1--27; the second campaign replaces this
  channel with sound voltage.
- A general statement that the four Kulite sensors were equally spaced along
  the x-axis and that obstacle distance and ignition location were varied.

## What is missing

The archive does not publish the case-by-case obstructed/unobstructed mapping,
obstacle type and dimensions, obstacle coordinates, ignition-code coordinates,
ignition delay, release origin/direction, pressure-sensor coordinates or the
equal spacing distance. The README explicitly states that ambient temperature,
humidity and wind were not documented.

These are model inputs, not optional annotations. Without them, an
apparatus-aware calculation cannot distinguish two experiments that share the
same pressure, nozzle and position code but have different turbulence,
flammable-cloud or sensor-distance conditions.

## Decision and next valid step

The retained source-only rank failure remains unchanged. No geometry coefficient
will be fitted to the consumed 44-case outcomes. A new comparison may proceed
only after the fields in
[`wskbij_apparatus_input_contract.schema.json`](wskbij_apparatus_input_contract.schema.json)
are supplied from a publisher-authenticated source and the model and thresholds
are frozen against a different outcome-unseen campaign.

The 2026 JoVE method article (DOI `10.3791/71000`) publicly confirms the general
experimental method, but its public metadata does not link numerical apparatus
dimensions to the WSKBIJ case identifiers. Those dimensions are therefore not
transferred into this dataset.

## Reproducibility boundary

The range reads cover only file headers and initial samples. File identities,
byte ranges and SHA-256 hashes are recorded in
[`wskbij_apparatus_metadata_audit_2026_10_08.json`](wskbij_apparatus_metadata_audit_2026_10_08.json).
This audit improves provenance and fail-closed behavior; it is not another
validation result and does not establish an outdoor HRS safety distance.
