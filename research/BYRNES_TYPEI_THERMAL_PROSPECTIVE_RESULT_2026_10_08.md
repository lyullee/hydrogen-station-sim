# Byrnes Type-I prospective thermal intake result

## Decision

**PROTOCOL_INVALID_PRIOR_OUTCOME_ACCESS**

The exact three `v0.50.0` GitHub files were opened after the attempted protocol
and local pressure-driven thermal model were committed as `b770af3`. A
repository-wide evidence check then found the same numerical YAML files had
already been accessed through Zenodo DOI `10.5281/zenodo.20728325` and scored in
`research/byrnes_zenodo_exploratory_result.json`. The GitHub location is a
duplicate source path, not a new holdout.

All three files contain a `gas_mean` series and a `wall_mean` series. The frozen
primary endpoint instead requires separate `gas_high` and `gas_low` series to
form a measured temperature envelope. Substituting the mean series after seeing
the schema would change both the observable and the score. The three files were
therefore retained, no file was replaced, no threshold or alias was changed,
and the numerical model was not run.

The prior-access discovery invalidates the prospective claim before any model
run. The channel mismatch is a second, independent exclusion. This is not
evidence that the thermal model failed a prediction and contributes no case to
the external thermal-validation gate. The existing Byrnes result remains
post-access exploratory evidence only.
