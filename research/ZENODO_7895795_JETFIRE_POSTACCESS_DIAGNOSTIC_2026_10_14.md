# Zenodo 7895795 high-pressure hydrogen jet-fire diagnostic

This artifact inventories nine publisher workbooks from the HyTunnel-CS/HSE
high-pressure hydrogen jet-fire campaign (DOI: [10.5281/zenodo.7895795](https://doi.org/10.5281/zenodo.7895795)).
The source reports actual-hydrogen releases that mimic a 700 bar vehicle TPRD,
including 2.1 mm and 0.57 mm nozzles, a 350 bar 5 mm case, vessel pressure,
free-jet thermocouples, impeded-jet temperature/pressure plates, and concrete
tests. The raw workbooks remain in the external quarantine directory and are
not redistributed in the repository.

The runner extracts the published vessel-pressure channel and computes a
descriptive initial/final pressure drop and half-pressure sample index. Where
the publisher gives explicit axial distances, it computes the peak temperature
rise relative to the first observation window and the Spearman trend with
distance. No release coefficient, heat-transfer coefficient, detector setting,
HyRAM parameter, or runtime parameter is fitted or changed.

The diagnostic found nine workbooks with pressure channels, six with thermal
channels, and two free-jet experiments with an explicit five-point axial
distance series. Both free-jet series showed a decreasing peak-temperature
rise with distance (test 1 rho = -0.70; test 2 rho = -1.00). These are
descriptive observations, not a calibrated heat-flux or radiation model.

## Provenance boundary

The files were opened before this artifact was created. The result is therefore
`POST_ACCESS_THERMAL_PRESSURE_DIAGNOSTIC_NOT_INDEPENDENT_VALIDATION`. It cannot
close a prospective holdout, pressure-decay, HyRAM consequence, safety-distance,
detector-placement, ESD-effectiveness, structural-damage, or station-to-vehicle
validation gate. It does not authorize runtime promotion. A future independent
use would require freezing the exact files and analysis before numerical access.

The machine-readable record is
`research/zenodo_7895795_jetfire_postaccess_diagnostic_2026_10_14.json`.
