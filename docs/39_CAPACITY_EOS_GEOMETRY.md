# Capacity/EOS vehicle geometry

The simulator now has an opt-in geometry basis for vehicle tanks. Set
`vehicle_geometry_basis` to `capacity_eos` and provide both
`vehicle_capacity_kg` and `vehicle_2_capacity_kg` in the simulation input.
Each internal volume is then calculated as:

```text
volume = declared_capacity_kg / rho_H2(working_pressure, 15 °C)
```

This physical gas volume is used once. The public Type-IV calibration's
effective-volume multiplier is therefore not applied again in this mode. Its
thermal gas-to-liner conductance calibration remains active when
`vehicle_tank_calibration=public_type_iv`; an explicit
`vehicle_effective_volume_multiplier` supplied by a research harness still
overrides the single-pass rule. This separation prevents a declared physical
volume from being corrected twice.

The density comes from the same generated hydrogen property table used by the
runtime solver. The default `reference` basis is unchanged, so existing runs
and published frozen results are reproducible. The capacity reference state is
explicitly 70 MPa and 15 °C for a 70 MPa vehicle; a vehicle configured for a
different nominal working pressure uses that pressure in the EOS lookup.

The rule was motivated by the public NREL H2FillS HDVS workbook. Its declared
9.8 kg tank capacity converts to approximately 0.24394 m³, whereas the legacy
linear reference geometry used 0.25438 m³. A seven-case geometry sensitivity
screen improved the exploratory pressure and mass metrics, but that workbook
had already been accessed when the comparison was made. Therefore the result
is development evidence, not an independent confirmatory validation, and the
new basis is not enabled by default.

A later eight-case MC Default transfer diagnostic also remained post-outcome
development evidence. It showed 4/8 joint screening passes for the single-pass
capacity/EOS geometry versus 0/8 with the frozen effective-volume multiplier,
but it cannot close an external-validation gate because those outcomes had
already been inspected. The result supports the software semantics above; it
does not support a validation claim or changing the default geometry basis.

The capacity fields do not identify or embed any private station, operator,
date, manufacturer, or raw operational data. Before using this basis as a
published default, freeze the geometry and all other fit parameters, then run
an untouched external holdout without tuning against it.
