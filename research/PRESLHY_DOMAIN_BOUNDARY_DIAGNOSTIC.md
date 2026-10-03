# PRESLHY domain-boundary diagnostic

This note records a post-outcome numerical diagnostic. It is deliberately
separate from the prospectively frozen `preslhy_blowdown_validation_protocol.json`
and must not be presented as a replacement validation claim.

## Problem reproduced

The frozen run retained several eligible cases as `ThermoDomainError` failures.
During late adiabatic blowdown, the hydrogen state cooled to the lower edge of
the tabulated property domain. The isentropic sonic point was below the
represented pressure–entropy curve, so the restriction solver correctly refused
to extrapolate. A second edge case occurred in the inverse `(density,
internal-energy)` lookup: neighboring density rows had slightly different
minimum energies at the 60 K table boundary, so a state inside the interpolated
surface could be rejected because it was a few joules outside one individual
row.

## Development change

The restriction solver now uses the finite lower-pressure flux at the
admissible table boundary when the sonic point lies below the represented
curve. The property inverse clamps its per-row seed to the tabulated endpoint
and then uses the existing bounded `(rho, T)` fallback if an exact inverse is
not represented. No pressure, temperature, entropy, density, or energy value is
extrapolated beyond the generated hydrogen table.

The change is covered by a regression test at a late PRESLHY 0.5 mm blowdown
state and by the existing restriction-lookup suite.

## New diagnostic result

The same 22 eligible cases and pre-existing source files were rerun with the
development implementation. The report is
`data/public_validation/results/preslhy_blowdown_domain_boundary/validation.json`.
The numerical screen fraction increased from 0.500 (11/22) in the frozen run to
0.727 (16/22), and the solver no longer produced a table-domain evaluation
error. This is a development signal, not an IJHE validation result: the
protocol was authored after the workbook outcomes were already inspected, so
the report explicitly marks `prospective_protocol: false` and
`ambient_direct_aperture_blowdown_claim_supported: false`.

The remaining failed cases are retained by case and pressure/diameter stratum.
The diagnostic does not change the frozen result, relax any endpoint, discard
failures, or fit a discharge coefficient.

## Next evidence required

Before using this implementation in an IJHE submission, freeze a new protocol
for an untouched external holdout, rerun without outcome-dependent changes, and
report all eligible failures. The PRESLHY result still validates only a rigid
vessel direct-aperture blowdown; it does not validate a complete station,
fueling loop, dispersion, ignition, or emergency response.
