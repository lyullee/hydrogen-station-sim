# Confidential station signal-consistency screen

## Purpose

This pre-attestation screen asked whether an owner-controlled station archive
contains an unambiguous instantaneous-flow/cumulative-totalizer pair that can
support the next storage-inventory calibration step. The implementation reads
the controlled files locally and serializes aggregate diagnostics only. It
does not retain paths, filenames, tag names, timestamps or measurement rows.

## Result

The screen examined 3,053,442 sampled rows from 20 pressure-and-flow tables. It
found 31 varying cumulative-like channels and 31 varying instantaneous-like
channels, producing 52 finite candidate comparisons. None met the deliberately
broad consistency screen of correlation at least 0.80 and span-normalized RMSE
at most 35%. The highest observed correlation was 0.522; the lowest individual
normalized RMSE was 24.83%, but it did not satisfy the joint criterion.

This is a useful negative result. Column-name heuristics and numerical shape
alone cannot identify the physical flow pair in this archive. Treating one of
these channels as calibrated mass flow would add an unsupported degree of
freedom and could make a source-volume fit look more certain than the evidence
allows.

## Decision

- Do not fit absolute mass flow or cascade volume from these unlabelled flow
  channels.
- Retain the already attested pressure and compressor-state evidence for the
  station-side recharge/restart-band diagnostics.
- Ask the data custodian only for the generic instantaneous/totalizer mapping,
  engineering units, sign/reset convention and calibration status. No company,
  site, date, manufacturer or public raw trace is needed.
- After that attestation, freeze the mapping and conversion before estimating a
  conditional storage compliance or effective aggregate volume.

The machine-readable aggregate is
`research/confidential_station_signal_consistency_screen_2026_10_08.json`.
This result neither validates station-to-vehicle filling nor establishes a
safety limit, consequence distance or field certification.
