# Frozen Jankuj 2026 pressure-decay transfer protocol

This protocol was frozen before downloading or opening the numerical archive for
Jankuj et al.'s 50 L, 200 bar hydrogen-cylinder penetration experiments.

- Article DOI: [10.1016/j.elstat.2025.104222](https://doi.org/10.1016/j.elstat.2025.104222)
- Dataset DOI: [10.5281/zenodo.17913628](https://doi.org/10.5281/zenodo.17913628)
- Dataset licence: CC BY 4.0
- Public metadata: two pressure curves sampled at 0.2 s, plus separate ignited
  and unignited temperature curves.

The first pressure curve is the development case. One effective breach diameter
is identified within 0.5--20 mm. The second curve is then evaluated without
refitting. Pressure NRMSE, median absolute percentage error and half-pressure
time error must all meet the thresholds in the JSON protocol.

The breach produced by projectile penetration is not geometrically documented,
so the fitted diameter is an effective flow area rather than a measured hole.
Ignition outcomes are excluded from fitting. Even a passing result would support
only repeat-transfer of the source-cylinder pressure-depletion submodel; it would
not validate ignition, H70 release, station operation, safety distance, emergency
response or SAGA effectiveness.
