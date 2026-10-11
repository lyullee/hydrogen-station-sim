# USN 17932439 pressure-peaking recheck (2026-10-11)

The DataverseNO release [10.23642/USN.17932439](https://doi.org/10.23642/USN.17932439)
contains ten public MATLAB records from actual-hydrogen pressure-peaking tests
in a 14.9 m³ confined, vented enclosure. The records expose `SIGMA` time and
mass-flow channels and `GEN3i` time and pressure channels. The raw files are
downloaded locally but remain ignored by Git; the companion JSON stores their
sizes and SHA-256 hashes.

## Replay

The fixed perfect-mix enclosure balance used by the earlier pressure-peaking
screen was replayed with the published vent-area mapping and fixed case
temperatures. No case-specific fitting, signal filtering, time shift, or case
selection was performed. The screening limits were absolute peak-pressure
error ≤ 5 kPa and peak-time error ≤ 20%.

| Result | Value |
|---|---:|
| Eligible cases | 10/10 |
| Joint screen passes | 8/10 |
| Joint pass fraction | 80% |
| Interpretation | Diagnostic only |

Cases 2 and 4 miss the peak-time screen; all other cases pass both diagnostic
screens. The result is encouraging for the enclosure pressure component, but it
is not a new confirmatory result: the public raw records were accessed before
this runner was created, and the fixed temperature/vent-area inputs are carried
from the earlier protocol. The result cannot validate an outdoor HRS, station
controller, vehicle fueling, dispersion distance, or emergency response.

Machine-readable output:
`research/usn_17932439_pressure_peaking_recheck_2026_10_11.json`.
