# MC Default thermal-observation diagnostic

The external MC Default replay has a channel labelled as a mean tank
temperature. The current Type-IV model separately evolves hydrogen-gas,
polymer-liner, and composite-shell temperatures. A label alone does not state
the sensor position, time constant, or averaging rule, so equating the source
channel with the model gas temperature is an unverified observation model.

`scripts/run_mc_temperature_observation_diagnostic.py` replays the eight
already-opened MC Default cases with the current runtime Type-IV parameters and
measured mass-flow, inlet-temperature, and source-pressure boundaries. It then
reports four predefined, non-fitted observation operators: gas, liner, shell,
and the unweighted liner/shell mean.

The result is stored in
`research/mc_temperature_observation_diagnostic_2026_10_07.json`. It retains
only case identifiers and derived metrics. It does not retain raw measurement
rows or source workbook names.

This is a post-outcome diagnostic. It does not select the lowest-error
operator, alter the runtime gas-temperature state used by the simulator, or
change the prospectively frozen full-loop result. A future validation campaign
must declare the physical thermal sensor location, calibration, response time,
and observation operator before its outcomes are evaluated.

Run it with:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\run_mc_temperature_observation_diagnostic.py
```
