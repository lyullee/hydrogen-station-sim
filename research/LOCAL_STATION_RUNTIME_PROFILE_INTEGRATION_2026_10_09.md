# Local station runtime profile integration audit

This audit runs two short API simulations against the committed sanitized aggregate profile.
The owner-controlled raw logger archive is never read by the runtime or written to the artifact.

| Case | Result | Profile | Restart margins (MPa) | Dynamics profile |
| --- | --- | --- | --- | --- |
| `reference_defaults` | `complete` | `reference_defaults` | `{'low': 2.0, 'medium': 3.0, 'high': 4.5}` | `disabled` |
| `explicit_opt_in` | `complete` | `owner_measured_operational_envelope_v1` | `{'low': 2.0, 'medium': 3.0, 'high': 4.5}` | `disabled` |

All checks passed: **True**

The aggregate 0.540 MPa measurement is retained as provenance, but it is
applied only as a conservative lower bound. It cannot overwrite an operator's
per-bank setting or the 4.5 MPa high-bank chronology criterion, preventing an
opt-in calibration switch from reintroducing rapid recharge cycling.

## Claim boundary

- The audit verifies API wiring and provenance for a sanitized station-boundary pressure profile.
- The measured profile is not a vehicle-side, full-loop, safety-limit or field-effect-distance validation.
- The recharge-dynamics candidate remains disabled because its chronological holdout was inconsistent.
- Raw logger rows, source identifiers, dates, paths and equipment identities are not published.
