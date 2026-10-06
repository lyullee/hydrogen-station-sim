# Confidential station-equipment operational envelope

This artifact records a privacy-bounded summary of one owner-controlled
station-equipment logger. The repository contains aggregate values only; raw
rows, source identifiers, exact dates, manufacturer/model information, and
tag names remain outside the repository.

## Observed evidence

- 1,426 sampled rows over 169,575 s.
- Storage-pressure observations: 56.295–63.260 MPa; median 60.8825 MPa.
- Station-temperature observations: -41.0–39.4 °C; median 0.2 °C.
- 44 discrete-state transitions.
- The pressure channel's boundary semantics were attested by the data
  custodian. Temperature boundary role and discrete-state semantics remain
  unattested.

## Use in the digital twin

The summary is exposed in the LLM evidence envelope as station-side operating
context. It can help the assistant distinguish an observed equipment envelope
from an arbitrary default and can support questions about plausible station
states. It does not automatically modify the production physics or operating
limits.

## Claim boundary

This is not vehicle-side validation, a synchronized station-to-vehicle
full-loop validation, a field safety-distance result, a failure-frequency
estimate, or a universal operating limit. Temperature and state values must
receive custodian attestation before they can be used for calibration. The
absence of vehicle-side channels is recorded explicitly so the LLM cannot
silently present this evidence as a complete fueling validation.

The machine-readable source of this summary is
`confidential_station_equipment_operational_envelope_2026_10_06.json`.
