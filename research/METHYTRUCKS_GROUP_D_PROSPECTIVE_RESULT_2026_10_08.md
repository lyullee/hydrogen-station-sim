# MetHyTrucks Group D prospective transient result

The frozen H70 workbook was downloaded only after protocol commit `8af1102`.
Its 69,408-byte file matched the publisher MD5, and the retained SHA-256 is
`51dcc909455bff6c7aa95c78cde2227f3e47ea809ef73abcab34c856010c8f0c`.
Raw rows remain in the gitignored data tree.

## Decision

**MODEL_SCREEN_NOT_RUN_INELIGIBLE_METADATA**

The workbook contains 720 samples on a strictly increasing 0.5 s time base.
The frozen alias rules resolve a flow channel, a delivered-temperature
candidate and an upstream-pressure candidate. They do not resolve vehicle tank
pressure or vehicle tank temperature. The generic `ValueY` headers provide no
machine-readable engineering units, and neither the workbook nor the official
context report identifies the selected vehicle's tank type and internal volume.

Several other pressure-like and temperature-like tags exist, but assigning them
to the vehicle would require a post-access guess. The protocol therefore
requires a retained metadata failure. No tank volume was inferred from final
pressure or transferred mass, no model parameter was fitted, and no numerical
prediction metric was produced.

This is a useful prospective negative result: it rules out the only previously
unopened MetHyTrucks H70 vehicle workbook as a self-contained validation case.
It contributes zero eligible cases toward the eight-case station full-loop
gate. Future acquisition must include explicit vehicle pressure and
temperature, tank geometry, engineering units, station/cascade states,
controller actions and calibration metadata.
