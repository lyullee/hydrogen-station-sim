# Cirrone delayed-ignition literature benchmark

The runtime now carries a separate conservative overpressure comparison based on
Cirrone et al., *Hydrogen* 3 (2022) 433–449,
[doi:10.3390/hydrogen3040027](https://doi.org/10.3390/hydrogen3040027).
The paper constructed Equation (5) from 78 ambient and cryogenic hydrogen
experiments.

The local implementation reproduces the paper's forward worked example
(70 MPa, 2 mm, 2.03 m: 21.9 kPa) and all 24 rounded radial distances in Table 4.
The maximum difference from a tabulated value is 0.044 m. The machine-readable
result is in `research/cirrone_2022_delayed_ignition_benchmark.json`.

The value is intentionally kept separate from the sampled HyRAM consequence.
It applies only to an under-expanded free jet and reports radial distance from
the centre of the 25–35 vol% hydrogen region. It is not the distance from the
leak, a site safety distance, an evacuation distance, or an accident
probability. Obstacles, jet impingement, confinement and site geometry are not
represented. A flow-limited line is marked not applicable because the paper's
pressure/diameter correlation does not represent that source boundary.
