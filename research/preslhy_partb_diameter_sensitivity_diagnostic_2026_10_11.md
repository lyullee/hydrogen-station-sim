# PRESLHY Part-B diameter sensitivity diagnostic (2026-10-11)

This is a **post-outcome development diagnostic**. It does not replace the
prospectively frozen result in `preslhy_partb_ambient_validation.json`, does not
change the 3/5 primary joint pass fraction, and must not be reported as a new
validation claim.

The frozen runner uses a single discharge coefficient (`Cd=0.8`) for all five
ambient cases. A controlled sensitivity grid was run only to test whether the
remaining timing error is diameter/regime dependent. The two 2 mm cases reach
their measured half-pressure time most closely near `Cd=0.6`; all three 4 mm
cases are closest near `Cd=0.7`. No single coefficient closes both groups, so a
single global refit would be physically misleading.

The result points to missing nozzle/manifold discharge-regime information rather
than a general wall-thermal error. A new prospective campaign would need the
effective aperture and edge geometry, upstream pressure/temperature at the
restriction, downstream pressure and line/manifold dimensions, and a
predeclared regime model or measured flow coefficient. Until then, the frozen
Part-B negative result remains unchanged.

Machine-readable sweep: `preslhy_partb_diameter_sensitivity_diagnostic_2026_10_11.json`.
