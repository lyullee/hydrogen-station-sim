# ELVHYS measured-signal HAZOP holdout protocol v2

The first prospective run failed before scoring because its frozen reader did
not define how real nonfinite concentration and trailing time values should be
handled. That failure is retained. Its 12 downloaded tests are development
data and are excluded from this second holdout.

Version 2 freezes all 15 remaining valid, uninspected dispersion tests. It
never imputes a concentration. Rows without a finite time are dropped; a head
requires 20 finite baseline observations; each timestamp uses the maximum of
the finite retained heads; and an all-missing timestamp is omitted. HAZOP
evaluation starts at the independently pressure-detected release onset.
Pre-release crossings remain a reported secondary diagnostic.

The primary screen requires all expected `GD-0101` ALARM/TRIP transitions to
occur with no unexpected transition, within one 20 Hz sample, and requires a
complete staged gas-release response plus public accident precedents. The
claim remains limited to measured-signal ingestion, persistence, severity and
response routing. It does not validate detector placement, concentration or
dispersion prediction, H70 transfer, ESD effectiveness, consequence distance,
or the complete station-to-vehicle model.
