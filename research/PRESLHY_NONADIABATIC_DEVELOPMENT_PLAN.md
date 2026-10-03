# PRESLHY non-adiabatic model-development plan

The prospectively evaluated adiabatic source-depletion model failed its
external validation: 11 of 22 eligible cases passed both frozen screens and
six high-pressure cases ended in a property-domain error. That result remains
the primary record for that model revision.

The same E3.1 Part A cases are now **consumed development evidence**. They may
explain the failure and guide a new physical model, but they cannot confirm it.
The revised model adds the published 28 kg stainless-steel vessel wall,
measured vessel geometry, internal natural convection, external convection at
6 W/m²/K, and a real-gas HEOS nozzle calculation. It retains the original
single discharge coefficient of 0.8 and does not fit a coefficient per test.

For diagnostic comparability, each development case is checked against the
original pressure NRMSE (≤10% of initial absolute pressure) and half-gauge-
pressure timing error (≤20%) screens. Any aggregate result is labelled
developmental. A new claim requires a model hash and evaluation protocol
frozen before numerical access to an independent holdout dataset.

Sources: PRESLHY E3.1 Part A, DOI 10.35097/1187; Cirrone et al.,
*Modelling the non-adiabatic blowdown of pressurised cryogenic hydrogen storage
tank*, DOI 10.1016/j.ijhydene.2023.05.182.
