# NBSDC Beijing Winter Olympics HRS intake protocol

This is the frozen, prospective intake contract for the NBSDC record
`CSTR:16666.11.nbsdc.aI3fJrzX`. The catalog and its file tree are public, but
the three numerical XLSX files currently require an approved data application.
No numerical validation claim is made from the catalog, the description file,
or the download probes.

## Expected package

The approved package should contain the description document plus the three
original workbooks: transaction records (`交易数据.xlsx`), dispenser records
(`加氢枪数据.xlsx`) and compressor records (`压缩机数据.xlsx`). File names may
be normalised by the custodian, but the original NBSDC file IDs and an immutable
SHA-256 for every received byte must be retained. `scripts/intake_external_hrs_bundle.py`
creates the byte-level manifest without opening a cell or parsing an archive.

## Promotion gates

The package is first promoted to **inventory ready** only when all four roles
are present and hashed. It can be promoted to **channel mapping eligible** only
when the custodian supplies the time base, timezone, sampling/aggregation rule,
units, missing-value codes, channel definitions and station topology. It can
enter the primary full-loop holdout only when untouched fills contain a common
time base, vehicle or receptacle pressure, vehicle/gas temperature, mass flow or
transferred mass, initial state and tank capacity, protocol or pressure ramp,
and stop/abort/alarm semantics.

Missing fields are retained as an explicit ineligibility reason. The pipeline
does not impute vehicle pressure, transferred mass, tank capacity or clock
alignment for the primary claim. A station-only or alarm/consequence analysis
may be reported separately, but it cannot be described as station-to-vehicle
closed-loop validation.

## Locked sequence

1. Record the approval decision and terms permitting derived metrics in the
   manuscript and repository.
2. Quarantine the files outside Git and hash them before reading numerical
   values.
3. Verify the four file roles and preserve the source IDs, sizes and digests.
4. Freeze the model commit, engineering screens, eligible-case rule and split.
5. Map declared aliases to the locked channel groups without fitting parameters.
6. Run the frozen model once on every eligible fill and retain failures.
7. Publish only de-identified derived traces, digests and allowed case metrics.

The general byte-level and metadata checks remain in
`research/EXTERNAL_HRS_INTAKE_PROTOCOL.md`. The machine-readable version of
this NBSDC-specific contract is
`research/nbsdc_winter_olympics_intake_protocol_2026_10_04.json`.

## Current status and claim boundary

The current public evidence verifies a credible real-HRS access route and the
declared file/channel scope. It does not provide the numerical workbooks or
rights to use them. Therefore the full-loop external-validation gate remains
closed, and no IJHE-level validation conclusion is permitted until the
custodian-approved package passes the locked numerical evaluation and the
independent SAGA effectiveness/safety review.
