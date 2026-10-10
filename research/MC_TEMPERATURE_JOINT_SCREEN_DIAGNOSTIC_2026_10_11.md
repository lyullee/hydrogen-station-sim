# MC temperature-operator joint-screen diagnostic (2026-10-11)

This is a **post-outcome semantic diagnostic**, not a new validation result.
The frozen MC Default vehicle-tank replay already supplies pressure and final
state-of-charge (SOC) errors. The source workbook labels its thermal channel
`tank_temperature_mean_c`, but does not identify whether that value represents
the gas, liner, shell, or a weighted sensor location. The diagnostic replays
the same co-located `Pinlet`/`Tinlet_G` boundary and evaluates four predefined
state operators:

- uniform gas temperature;
- inner liner temperature;
- outer shell temperature;
- unweighted liner/shell mean.

For each operator, the frozen limits remain pressure RMSE ≤ 5 MPa, temperature
RMSE ≤ 10 °C, and absolute final SOC error ≤ 5 percentage points. Pressure and
SOC are inherited from the frozen boundary report; only the temperature
operator is varied. Therefore a candidate cannot pass by changing the model,
fitting parameters, or selecting an operator after seeing the outcomes.

The committed JSON report shows **0/8 joint passes for every candidate
operator**. This means that clarifying the temperature label alone does not
resolve the MC boundary failure; pressure/SOC or another pre-specified model or
measurement boundary must be addressed. No runtime parameter, frozen holdout,
readiness gate, or full-loop claim was changed.

Evidence: `research/mc_temperature_joint_screen_diagnostic_2026_10_11.json`.
