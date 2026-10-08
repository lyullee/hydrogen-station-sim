# Controlled full-loop cohort registry

This registry is an intake boundary for a future station-to-vehicle holdout. It records the large local station-side data coverage and the missing vehicle-side attestation without publishing raw rows, source names, exact dates, site identity or manufacturer details.

The current local collection contains 33 measured station files (4.749 GiB; 59,272,300 physical rows and 56,854,143 rows after duplicate exclusion). It supports pressure-cycle, cascade and recharge analysis. No synchronized vehicle pressure/temperature and delivered-mass or SOC channel has been attested, so the registry intentionally contains zero eligible cases and `full_loop_external_validation_supported: false`.

Promotion requires a pre-outcome freeze, at least eight disjoint fills, the complete channel contract in the JSON registry, rights clearance for reviewer/reproduction use, and the frozen numerical screens. A draft registry must never be interpreted as external validation.
