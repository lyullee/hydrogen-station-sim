# Apparatus valve-timing evidence and development boundary — 2026-10-11

## Evidence

The DISCHA unignited hydrogen-release campaign describes a pneumatic ball
valve with an approximately 40 ms command-to-motion delay and a further
approximately 180 ms to reach the full cross-section. The paper also states
that the first pressure rise in the release-line sensor was used as the
release-time reference. The source is the open conference paper:

- Jordan et al., *Hydrogen blowdown release experiments at KIT* (ICHS 2021),
  [PDF](https://hysafe.info/uploads/papers/2021/38.pdf), especially pp. 7--8.

These values are source-reported apparatus context. They are not a fitted
parameter and are not transferred to the production station model.

## Development change

`src/h2station/release_network.py` now supports independent
`upstream_valve_delay_s` and `terminal_valve_delay_s` inputs. A delay holds the
corresponding boundary at its initial opening fraction before the declared
opening ramp begins. The defaults are zero, so the existing v1 behavior is
unchanged until an apparatus declares a delay.

The new behavior is covered by a conservation test and remains in the
prospective apparatus-resolved development path. It does not alter the frozen
Schefer, Proust, PRESLHY or Grüne results and does not create an external
validation claim. A future campaign must provide time-resolved valve position
or an independently justified command-to-motion measurement before choosing
non-zero values.

## Claim boundary

This artifact supports model-structure provenance only. It does not establish
station-control accuracy, vehicle-fill accuracy, ignition/dispersion accuracy,
safety distance, regulatory compliance or SAGA effectiveness.
