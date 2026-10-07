# Confidential station recharge multi-trace recheck

This recheck evaluates whether a compressor restart dwell derived from restricted station logs generalizes across repeated operation. Raw rows, source paths, organization and site identity, exact dates, equipment manufacturers, model names and private tag names remain outside the repository.

## Design

Eight de-identified station-side traces share owner-attested medium/high storage-pressure roles and a compressor loaded-state role. Each trace is split chronologically: the first 70% estimates a restart-dwell candidate and the final 30% is untouched by that estimate. Runtime eligibility requires at least three completed holdout OFF-to-ON intervals and every completed interval to be no shorter than the fitted dwell.

## Result

| Measure | Result |
|---|---:|
| Calibration traces | 8 |
| Calibration samples | 457,405 |
| Calibration state transitions | 190 |
| Completed calibration OFF-to-ON intervals | 89 |
| Fitted restart-dwell candidate | 290.0 s |
| Holdout traces | 8 |
| Holdout samples | 196,037 |
| Completed holdout OFF-to-ON intervals | 32 |
| Shortest holdout OFF-to-ON interval | 176.0 s |
| Runtime application | **Blocked** |

The holdout contains a completed restart sooner than the fitted candidate. The multi-trace gate therefore fails. The earlier single-trace 265.2 s result is superseded and cannot be used as the simulator default or an opt-in parameter.

## Software decision

- The runtime profile loader now reads the multi-trace artifact and rejects it because `runtime_parameter_application` is false.
- The API default is reference control, and the remote-control option is visibly locked.
- The LLM evidence envelope retains the negative result, candidate value, holdout minimum and block reason so a response cannot silently present the candidate as applied calibration.
- The old single-trace artifact remains only for audit history and explicitly points to the superseding result.

This is a station-side controller-behavior check. It does not validate compressor capacity, vehicle filling, SAE J2601 compliance, consequence distance, accident frequency or the station-to-vehicle loop.
