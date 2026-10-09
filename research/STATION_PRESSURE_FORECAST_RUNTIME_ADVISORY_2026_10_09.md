# Station pressure forecast runtime advisory

The simulator now exposes a short-horizon pressure forecast when the pressure-recharge operation is flowing and a causal ten-second prefix is available. The advisory uses the already frozen, same-site station-side holdout:

- 1,024 calibration cases and 394 chronological holdout cases
- median absolute error: **0.055 MPa**
- 90th-percentile absolute error: **0.529255 MPa**
- mean absolute error improvement over persistence: **71.8855%**
- positive-direction agreement: **94.9239%**

The runtime selects a dominant positive rise in the medium or high bank, applies the holdout continuation gain for that bank, and reports the current pressure, 30-second forecast and provenance. It fails closed during idle/startup, with insufficient history, or when neither bank has a dominant response.

This is an advisory signal for the digital twin and LLM prompt. It does not modify the physical simulator, compressor capacity, recharge restart margins, safety limits or ESD logic. It does not validate vehicle filling, storage geometry, consequence distances or a complete station-to-vehicle loop.

Implementation: [`src/h2station/station_pressure_forecast.py`](../src/h2station/station_pressure_forecast.py). The API carries the value as `station_pressure_forecast`; the evidence manifest carries the same claim boundary to the LLM.

## Interactive provenance

The compact evidence envelope now exposes `data_used` in the selected-sensor
and pressure-forecast views. It reports
the bounded sensor tags, impact-calculation status, and forecast status used for
that answer. It does not expose private file names, raw rows, site identifiers,
or unpublished channel mappings. The detailed audit manifest and its digest
remain available to the API/UI for traceability.
