# Confidential station signal-consistency screen

## Purpose

This pre-attestation screen asked whether an owner-controlled station archive
contains internally coherent instantaneous-flow/cumulative-totalizer pairs
that can support the next storage-inventory calibration step. The
implementation reads the controlled files locally and serializes aggregate
diagnostics only. It does not retain paths, filenames, tag names, timestamps or
measurement rows.

The revised screen evaluates fixed 1, 10, 30 and 60 second aggregation windows.
This prevents a slowly updating or quantized totalizer from being rejected only
because its one-second derivative alternates between zero and discrete jumps.
The windows and acceptance thresholds were fixed in code before this rerun.

## Result

The screen examined 3,053,442 sampled rows from 20 pressure-and-flow tables. It
found 31 varying cumulative-like channels and 31 varying instantaneous-like
channels, producing 54 finite candidate comparisons. Twenty-seven comparisons
in 17 files met the consistency screen of correlation at least 0.80 and
span-normalized RMSE at most 35%.

Among the passing comparisons, median correlation was 0.9971, median
span-normalized RMSE was 2.54%, and the median selected aggregation window was
60 seconds. The median derivative-to-signal scale was 0.016648, close to 1/60.
This is strong internal evidence for a recurring compatible
instantaneous/totalizer relationship and is consistent with, but does not by
itself attest, a per-minute instantaneous-flow convention relative to a
per-second totalizer derivative.

## Decision

- Treat the archive as containing candidate instantaneous/totalizer pairs
  suitable for targeted custodian attestation and a frozen follow-up analysis.
- Do not yet fit absolute mass flow or cascade volume: channel roles,
  engineering units, sign/reset convention and calibration status remain
  unattested.
- Retain the already supported station-side pressure, temperature,
  compressor-state and restart-band diagnostics.
- Keep station-side dynamic consistency separate from vehicle-fill and
  station-to-vehicle validation because the archive contains no vehicle-side
  channels.
- Record this as a post-access diagnostic improvement, not an independent
  holdout result or safety certification.

The machine-readable aggregate is
`research/confidential_station_signal_consistency_screen_2026_10_08.json`.
This result neither validates station-to-vehicle filling nor establishes a
safety limit, consequence distance or field certification.
