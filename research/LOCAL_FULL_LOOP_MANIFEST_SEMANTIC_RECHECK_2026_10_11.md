# Local full-loop candidate semantic recheck (2026-10-11)

The private candidate manifest was re-screened using two conditions together:
the header must contain station-side pressure, vehicle-side pressure and
temperature, a common time field, mass/flow, and control or ESD context; and
the file must contain at least one data row. The result stores only aggregate
counts and does not publish paths, filenames, headers, identifiers, dates, or
raw values.

The manifest contained 247 existing CSV/TSV files. One file matched the broad
full-loop schema, but it was an empty schema template. No candidate had both a
complete full-loop schema and non-empty measured rows. The measured full-loop
candidate count is therefore zero and no holdout or runtime validation gate is
opened.

This screen is a triage result, not validation. A future candidate still needs
pre-access freezing, engineering-unit and role attestation, rights/custodian
confirmation, checksum capture, and independent scoring before it can support
the external-validation claim.

See `local_full_loop_manifest_semantic_recheck_2026_10_11.json` for the
privacy-bounded machine-readable record.
