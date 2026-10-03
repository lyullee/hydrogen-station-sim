# Consequence geometry validation chain

- Status: **PASSED**
- Scope: outdoor unconfined hydrogen free-jet consequence display mapping
- Independent evidence families: **3**
- Site-specific validation: **No**
- Safety-distance claim permitted: **No**

## Evidence chain

| Family | Published experiment | Production/display quantity | Geometry |
|---|---|---|---|
| `four_percent_unignited_plume` | Han et al. (2013), Figure 6 | flammable_plume_streamline_distance_m | directional free-jet centerline length |
| `ignited_jet_radiation` | Schefer et al. (2006), Figure 8; Houf and Schefer (2007), Figure 6 | heat_fluxes and sampled 5 kW/m2 threshold bracket | sampled radial screening distance |
| `unconfined_overpressure` | Bauwens and Dorofeev (2019), Figure 9; additional published sets in the same suite | overpressures and sampled 5 kPa threshold bracket | sampled radial screening distance |

## Automated chain checks

- [x] `exact_hyram_source_identity`
- [x] `upstream_validation_passed`
- [x] `required_upstream_modules_executed`
- [x] `production_adapter_parity_passed`
- [x] `production_contract_preserves_geometry_inputs`
- [x] `display_separates_radial_and_directional_geometry`
- [x] `browser_mapping_regression_passed`
- [x] `all_evidence_markers_and_data_present`

## Interpretation

The traceability chain passes for the bounded outdoor free-jet display scope. It does not validate a specific station site or authorize a safety-distance claim.

The experimental-model layer is the exact HyRAM+ 6.1 source already verified against the frozen upstream suite. The production adapter has exact numerical parity for plume, heat-flux and overpressure outputs. The browser contract now keeps radial thermal/blast screening separate from the directional 4 vol% plume instead of collapsing both into one dome.

Primary validation reference: [Validation of HyRAM+ Version 5.1 Physics Models](https://doi.org/10.2172/2480221). Official software context: [Sandia HyRAM+](https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/).

## Limitations

- The independent measurements are published data digitized and regression-tested by HyRAM+, not measurements produced by this project.
- The display is a screening visualization, not a regulatory separation distance, evacuation radius, or certified safety boundary.
- Buildings, congestion, terrain and site-specific wind are not resolved; no site-specific CFD or outdoor field campaign has been performed.
- The 5 kW/m2 and 5 kPa radial result is a discrete observation-point bracket and must not be interpolated as an exact contour.
- Unconfined overpressure depends on the selected BST flame-speed assumption; alternate methods remain a model-form sensitivity.
- The scene uses the stored release elevation angle but a schematic +X azimuth because the process model does not provide site azimuth.
