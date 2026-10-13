# ELVHYS WP4.2 spatial holdout protocol

This protocol is frozen before opening the numerical files for the public **ELVHYS 4.2** dataset (DOI `10.18710/JXJP0H`). The dataset is published by DataverseNO under CC0 1.0 and describes 48 actual liquid-hydrogen experiments in a 1 m³ transfer-connection space.

The evaluation is restricted to unignited small horizontal or vertical leak dispersion cases. Pressure-peaking and deliberately ignited tests are excluded before numerical access because they represent different response regimes. Every eligible case must provide source and sensor coordinates in a common frame, coordinate units, release orientation, a release interval, and numerical hydrogen concentration values for at least eight scored observations. At least ten eligible cases are required.

The frozen `pooled_spatial_rank_v1` candidate is evaluated without tuning. The response is q99 minus q10 hydrogen concentration during the publisher-authenticated release interval. The locked screens are median within-case Spearman rho ≥ 0.5, at least 60% of cases with rho ≥ 0.4, mean top-five recall ≥ 0.6, and nearest predicted observation in the observed top quartile for at least 70% of cases. All screens and all declared eligible cases must pass.

The result can support only spatial response ordering in this cryogenic indoor geometry. It cannot validate outdoor HRS detector placement, concentration magnitude, detector response time, CFD, consequence distance, ESD effectiveness or field safety. Raw CSV files will not be committed; only hashes, parsing diagnostics and derived aggregate results are retained.
