# PRESLHY E5.1 domain-boundary diagnostic

This is a post-outcome development diagnostic. It is separate from the frozen
PRESLHY E5.1 holdout result and cannot replace that result or support a new
prospective validation claim.

The current bounded hydrogen-property implementation was run against all seven
records in the public E5.1 benchmark archive. The ambient primary subset still
contains three eligible cases, with two joint primary passes (0.667). The
eligibility minimum requires four ambient cases and a 0.700 pass fraction, so
the aggregate claim remains unsupported. The result is therefore unchanged by
the table-boundary correction.

Three records remain retained failures because their source-pressure traces
have excessive post-release increases under the frozen eligibility rule. They
are not silently removed or reclassified.

The machine-readable result is
`data/public_validation/results/preslhy_e5_domain_boundary_diagnostic.json`.
It records `prospective_protocol: false` and `claim_supported: false`.
