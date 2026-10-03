# PRESLHY E5.1 independent holdout protocol

This protocol was frozen on 2026-10-03 before downloading or opening the E5.1
numerical archive. The revised model implementation is locked by SHA-256 in the
machine-readable protocol. Its 22 E3.1 Part A cases are consumed development
evidence and cannot confirm the revision.

## Primary question

Can the locked non-adiabatic model predict source-vessel pressure depletion in
previously unused ambient-temperature E5.1 open-jet ignition experiments?
The full source-pressure trace remains in scope after ignition. This tests,
rather than assumes, whether the downstream open flame has negligible feedback
on source depletion under the published conditions.

Each case must have source pressure, an in-vessel initial temperature, a
recoverable release time zero, and at least 20 post-release samples. The primary
ambient subset is 280–330 K, 0.5–21 MPa absolute, and 1–4 mm nominal nozzle
diameter. Cryogenic cases are reported separately as transfer tests.

The frozen case screens are pressure NRMSE ≤10% of initial absolute pressure
and half-initial-gauge-pressure timing error ≤20%. A positive aggregate decision
requires at least four cases, two nozzle sizes, two initial-pressure groups, and
at least 70% passing both screens. If the public benchmarking package is too
narrow, the result is retained as supplementary evidence and is ineligible for
the aggregate claim.

The archive was inspected only to implement a structural reader. The publisher
package contains five ambient and two cryogenic experiments; the ambient set
spans 2 and 4 mm nozzles and nominal 50 and 200 bar conditions. Before any
numerical pressure value or model outcome was read, the case manifest, reader,
runner, acquisition code, and their hashes were recorded in the machine-readable
protocol. No model change is allowed.

Dataset: Jordan (2023), PRESLHY E5.1, DOI 10.35097/1258, CC BY-SA 4.0.
