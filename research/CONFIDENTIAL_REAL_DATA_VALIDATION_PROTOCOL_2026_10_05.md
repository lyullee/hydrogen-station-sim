# Confidential real-station data validation protocol

This project may use real hydrogen-station operational data that cannot be
redistributed. The raw files must remain with the data owner or in an
institution-approved restricted repository. They must not be copied into this
Git repository, Zenodo, public issue trackers, or public model prompts.

## What can be published

- a data-custodian description and the measurement schema;
- a cryptographic digest of the quarantined archive, if the custodian permits
  publication of the digest;
- de-identified case identifiers and relative time axes;
- aggregate errors, confidence intervals, pass/fail rules, and uncertainty
  bounds;
- synthetic traces with the same schema for software reproduction;
- the frozen scoring code and model commit.

Exact station identifiers, coordinates, calendar timestamps, controller
recipes, proprietary set-points, security-relevant topology, personal data,
and raw sensor rows remain restricted.

## Controlled validation workflow

1. Obtain written permission or an institutional data-use agreement describing
   the permitted scientific use, reviewer access, retention period, and whether
   derived metrics may be published.
2. Create a manifest and SHA-256 digest before opening outcome values. Record
   the custodian, licence/permission boundary, file count, channel dictionary,
   units, calibration metadata, and time-zone policy.
3. Quarantine the archive in an access-controlled location. Freeze the model
   commit, scoring protocol, case-selection rule, and acceptance thresholds
   before numerical outcomes are inspected.
4. Remove or pseudonymise station and vehicle identifiers. Preserve the
   physical relationships needed for validation, including synchronized time,
   pressure, temperature, mass-flow, dispenser/nozzle, source-bank and vehicle
   channels where permission allows.
5. Keep every case, including failures. Do not tune on the restricted holdout
   and do not replace a failure with a synthetic or chart-digitised case.
6. Publish only approved aggregates and a synthetic reproduction package. Give
   the editor and reviewers a controlled inspection path when the journal or
   data owner requires raw-data verification.

## Claim boundary

Confidential data can support an externally evaluated result when provenance,
access controls, pre-outcome freezing, and reviewer verification are recorded.
Confidentiality alone does not make a result a validation: the archive still
needs synchronized channels, independent cases, fixed scoring, and permission
to report the derived results. If reviewer access cannot be arranged, the
manuscript must narrow its claim and state that the raw validation data are not
publicly reproducible.

## Repository rule

Only this protocol, the schema, approved derived metrics, and synthetic traces
belong in the public repository. A local private-data path or API credential
must never be committed.
