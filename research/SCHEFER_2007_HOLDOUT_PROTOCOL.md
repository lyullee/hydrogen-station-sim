# Schefer et al. (2007) pressure-decay holdout protocol

This protocol freezes an experiment-level transfer test before the numerical
coordinates of the target pressure curve are opened. The public apparatus
inputs are 43.1 MPa absolute, 290 K, a 1.234 m3 vessel and a 5.08 mm
restriction. The locked model is the existing HEOS, well-mixed adiabatic vessel
balance with `Cd = 1.0`; the target trace cannot be used to alter it.

The primary claim requires all three screens to pass: pressure NRMSE no greater
than 10% of measured initial pressure, median absolute percentage error no
greater than 15% over the main trace, and half-pressure-time error no greater
than 20%. At least 15 unique experimental coordinates are required. Failures
and ineligible outcomes are retained.

The data are the HyRAM+ 6.1 digitization of Figure 4 from Schefer et al.,
*Characterization of high-pressure, underexpanded hydrogen-jet flames*,
International Journal of Hydrogen Energy 32 (2007) 2081-2093,
https://doi.org/10.1016/j.ijhydene.2006.08.037. The digitization is attributed
to HyRAM+ commit `b45abf9a6d995951311be6aad836f1874e4d420b` under GPL-3.0.

This test is bounded to vessel pressure decay. It does not establish station
control, flame, radiation, dispersion, or separation-distance validity.
