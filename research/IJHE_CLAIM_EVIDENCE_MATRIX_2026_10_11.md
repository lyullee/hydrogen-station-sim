# IJHE claim/evidence matrix (2026-10-14)

This reviewer-facing companion is generated from `manuscript/ijhe_readiness_audit.json`.
It records bounded component claims and preserves failed or incomplete transfers.
It does not establish journal acceptance, field safety, or human-effectiveness.

Audit SHA-256: `48568765a898a49813a2cb5d185d4899cd3dfaaace0b6db2dd37797801af85b9`

| Claim boundary | Evidence | Decision | Interpretation |
|---|---|---|---|
| Measured-boundary Type-IV tank thermodynamics | 12 independent public fills; pressure, temperature and SOC | PASS | Tank submodel only; not cascade dispatch, precooling or vehicle-control validation. |
| Type-III thermal transfer | Independent prospective fill | FAIL | Pressure screens passed, but gas-temperature screens failed; no temperature-transfer claim. |
| Ambient PRESLHY source depletion | Five Part-B cases | FAIL | Joint screen below the declared threshold; diameter-dependent boundary sensitivity remains unresolved. |
| 90 MPa aperture release | Three INERIS/CEA series | FAIL | No series met the joint mass-flow rule; no universal aperture correction is supported. |
| Transient blowdown source model | Sandia/SRI 2006 trace | FAIL | Peak-normalized NRMSE passed, but median error and half-peak timing failed. |
| Ignited-enclosure consequence endpoint | Installed HyRAM+ API and 27 ignited-enclosure cases | PASS | Adapter and bounded enclosure peak-pressure translation only; not site consequence or separation-distance certification. |
| Spatial detector transfer | 18 actual-hydrogen HyTunnel cases | FAIL | Rank/recall screens were not jointly met; geometry-only routing remains disabled at runtime. |
| Station-to-vehicle full loop | Public-data search and consumed closed-loop diagnostic | OUT OF SCOPE | Out of scope: no rights-cleared synchronized station/controller/dispenser/vehicle raw cohort was found. |

The detailed endpoint values, protocol hashes and source paths remain in the JSON audit.
A passing component is never promoted to a complete station-to-vehicle claim.
