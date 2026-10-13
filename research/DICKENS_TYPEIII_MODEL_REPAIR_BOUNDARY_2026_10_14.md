# Dickens Type-III model-repair boundary (2026-10-14)

This note records the highest-impact repair boundary for the frozen Dickens
Type-III filling result. It is deliberately separate from the validation gate:
the original prospective result remains failed for the gas-temperature
screens, and no post-outcome result is promoted to the runtime model.

## What the current evidence says

- The frozen result has a pressure fit but fails the reported gas-temperature
  observation screens.
- A post-outcome observation replay gives much smaller error for the predefined
  unweighted gas/liner mean than for the gas state alone. This exposes an
  observation-semantic ambiguity; it does not identify the publisher's sensor
  operator.
- A post-outcome forced-convection sensitivity passes the diagnostic screens at
  3, 5, and 7 mm inlet-nozzle diameters. Because the experiment's inlet-nozzle
  diameter and time-resolved inlet-gas temperature are not disclosed in the
  frozen source package, none of these values can be selected for runtime use.
- The default station and vehicle runtime path remains `constant_ua`. The
  `mixed_convection` path requires explicit physical tank geometry and inlet
  nozzle geometry and is opt-in only.

## Required evidence before a repair can be promoted

The next independent holdout must be frozen before case-level outcomes are
opened and must provide all of the following:

1. inlet-nozzle internal diameter and the metrology/uncertainty;
2. time-resolved inlet-gas temperature or a publisher-authenticated boundary
   temperature definition;
3. the temperature sensor location and response/averaging definition;
4. gas, liner and shell state mapping sufficient to define the observation
   operator without choosing the operator from model error;
5. an outcome-unseen acceptance rule for pressure, gas temperature and peak
   temperature.

Until those inputs exist, the only permitted use of the two diagnostics is
model-development explanation. They may not change a validation gate, a
runtime parameter, a safety-distance calculation, or an LLM evidence claim.

Machine-readable enforcement is in
`research/dickens_typeiii_model_repair_boundary_2026_10_14.json` and is covered
by `tests/test_dickens_typeiii_model_repair_boundary.py`.
