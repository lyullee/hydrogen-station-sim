# H2Protocol case inventory recheck (2026-10-05)

The downloaded H2Protocol archives contain 36 SAE J2601 Tables Method cases and
8 MC Default cases.  The inventory was generated from the processed case index
and the committed result manifests, with the archive SHA-256 values retained in
the accompanying JSON record.

All Tables Method cases already occur in an inspected tank-model or closed-loop
record.  `H2P-L10` is excluded by the current mass-closure quality screen, but
it is not a fresh case because its outcome was already inspected.  All eight MC
Default cases are in the frozen external holdout.  Therefore there is no
uninspected H2Protocol case that can honestly be promoted to a new independent
full-loop holdout in this repository.

This is an intake boundary, not a validation result.  The downloaded files are
used locally for verification; no redistribution or publication permission is
inferred from the download page.  The full-loop gate remains open until an
independent synchronized station-to-vehicle archive is obtained, rights are
recorded, and a no-fitting scoring protocol is frozen before outcomes are read.

Machine-readable record: `research/h2protocol_case_inventory_recheck_2026_10_05.json`.
