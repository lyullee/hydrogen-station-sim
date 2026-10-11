# Proust release boundary-semantics diagnostic

This record is a **post-outcome diagnostic only**. It does not change the
prospectively frozen Proust holdout, choose a new discharge coefficient, or
activate a new runtime model.

The frozen direct-aperture result failed all three required diameter groups.
The diagnostic recomputes the measured-to-unit-coefficient ratio at every
digitized state and records the apparatus information needed to design a new
network-resolved experiment. The nominal published apparatus contains a 25 L
source, a 10 m by 10 mm supply line, a valve opening of about 0.1 s, and 1--3
mm terminal orifices. The current holdout pairs source/reservoir pressure with
an upstream/near-orifice temperature observation, but does not expose line
pressure, line temperature, valve position, as-built bore or dead volume.

The resulting effective coefficient is diameter dependent: the 1 mm series is
above the inherited 0.8 convention while the 2 and 3 mm series are below it.
That pattern is not a defensible global calibration. It is evidence that a
terminal-only boundary is insufficient for this apparatus or that the plotted
pressure/temperature locations do not represent one common stagnation state.

The machine-readable values and hashes are in
[`proust_release_boundary_semantics_diagnostic_2026_10_12.json`](proust_release_boundary_semantics_diagnostic_2026_10_12.json).
The primary negative result remains
[`proust_release_holdout_result.json`](proust_release_holdout_result.json).

Promotion requires rights-cleared synchronized line/valve/terminal data, a new
predeclared network protocol, and a new independent holdout. No production
parameter or safety-distance claim is changed by this diagnostic.
