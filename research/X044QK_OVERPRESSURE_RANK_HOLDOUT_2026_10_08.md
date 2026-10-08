# X044QK actual-hydrogen overpressure-rank holdout

## Outcome

The six-case raw-trace protocol was committed before any selected pressure trace
was opened. It balanced the two obstacle distances (29 cm and 54 cm) and all
three published ignition positions, and it prohibited case replacement,
post-access threshold changes and outcome-specific model tuning.

The numerical screen was **not run**. A 256 KiB range read of the first selected
publisher file was sufficient to identify the schema before entering the
outcome window. The file provides time in milliseconds, a trigger channel, four
dynamic-pressure channels and the nozzle-pressure channel, but every measured
channel is stored in volts. The public README and method descriptions identify
the sensor family and acquisition system but do not provide the charge-amplifier
conversion used for these files.

The frozen protocol explicitly requires engineering pressure units or a
publisher-documented calibration. The run therefore failed closed as
`MODEL_SCREEN_NOT_RUN_INELIGIBLE_UNCALIBRATED_PRESSURE_VOLTAGE`. No pressure
peak was calculated, the other five large raw files were not downloaded, HyRAM
was not executed and no runtime parameter changed.

## Why the voltage traces were not ranked

A common positive scale factor would preserve rank, but assuming a common
calibration across sensors and tests after opening the raw schema would weaken
the frozen eligibility rule. Sensor-specific charge-amplifier settings can also
change voltage amplitudes. The correct next evidence is a publisher-authenticated
calibration or a revised archive in engineering pressure units, followed by a
new protocol version frozen before outcome-window access.

## Evidence

- Dataset: <https://doi.org/10.18710/X044QK>
- Associated article: <https://doi.org/10.1016/j.firesaf.2026.104812>
- Method article: <https://www.jove.com/t/71000/high-speed-visualization-pressure-measurement-hydrogen-explosion>
- Frozen protocol: `research/x044qk_overpressure_rank_holdout_protocol_2026_10_08.json`
- Result: `research/x044qk_overpressure_rank_holdout_result_2026_10_08.json`
- Raw CSV rows committed: **no**

## Claim boundary

This is a retained prospective negative intake result. It demonstrates a
calibration-metadata limitation in the public release; it is neither a numerical
HyRAM failure nor validation of absolute overpressure, relative severity,
outdoor HRS geometry, consequence distance, injury risk or the full digital
twin.
