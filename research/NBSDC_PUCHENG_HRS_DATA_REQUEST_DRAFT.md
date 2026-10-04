# NBSDC Pucheng HRS operational-data request

This draft is a request template only. It does not authorize contact and does
not treat the catalog or its description document as validation evidence.

## Candidate and provenance

- Dataset: **Engineering Demonstration of Smart Emergency Decision-Making Platform for Hydrogen Fire and Explosion Accident**
- CSTR: `CSTR:16666.11.nbsdc.wvSgtxVy`
- Catalog: <https://www.nbsdc.cn/general/dataDetail?id=67fb63bb195d26544804482c&type=1>
- Station: Pucheng demonstration HRS, 1000 kg/d class
- Declared collection: 2024-11-23 through 2024-11-27 at 10 s sampling
- Public description digest: `e013dbbe3700679b228025beefdb741a1ebcfc2a5629c33a00dea74ccdb15e1f`

## Requested export

Please provide a de-identified copy of the twelve station-monitoring
workbooks, their SHA-256 digests, and a data dictionary covering:

1. Dispenser nozzle pressure, flow, inlet-gas and ambient temperature,
   real-time/cumulative dispensed mass, start/end pressure and mass, vehicle
   cylinder volume, fill start/end timestamps and dispenser state.
2. Storage-cylinder pressure, temperature, volume, bank identity and fault
   state for low/mid/high pressure banks.
3. Liquid-driven and diaphragm-compressor pressure, temperature, detector,
   valve-position, run/fault/ESD and sequence-control channels.
4. Unloading-column pressure, temperature, mass, valve state and trailer
   transfer state.
5. Hydrogen, flame and oxygen detector channels; alarm, ESD, maintenance,
   aborted-fill and sensor-calibration flags.
6. Time-zone, clock-synchronization, sampling/aggregation rules, units,
   missing-value codes and any sensor quality flags.

Please also provide station topology and protocol/initial-condition metadata
so that source, cascade, compressor, precooler, dispenser and vehicle-side
channels can be mapped without inference. If vehicle or receptacle pressure,
temperature and transferred mass are not available, state that explicitly so
the files can be used only for station-state and alarm/consequence studies.

## Rights requested

Please confirm that the data can be used for a reproducible research study,
that de-identified derived traces and case-level error metrics may be deposited
in an open repository, and that those derived results may be published in the
*International Journal of Hydrogen Energy*. Raw files need not be redistributed
if the custodian requires controlled access; in that case, retain the access
decision, immutable file digest and a public metadata record.

## Quarantine and validation plan

On receipt, files will be copied to a gitignored quarantine directory and
hashed before opening any outcome values. A protocol will be frozen first,
including eligible channels, case split, model commit, engineering screens and
no-fitting rules. The model will then be run once on every eligible case; no
case-specific fitting, time warping or post-outcome parameter changes will be
allowed. Missing vehicle-side channels will be reported as an eligibility
failure rather than silently imputed.

Current status: the portal exposes a public file manifest and downloadable
description, but the monitoring workbooks require an approved data application.
