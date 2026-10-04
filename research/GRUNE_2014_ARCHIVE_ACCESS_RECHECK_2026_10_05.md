# Grune 2014 / Zenodo archive access recheck

Generated on 2026-10-05 from the complete local copy of the public Zenodo
record [10.5281/zenodo.4668554](https://doi.org/10.5281/zenodo.4668554),
which is marked CC BY 4.0.  The source is the ventilation/concentration
archive associated with Grune et al. (2014), not a new pressure-decay archive.

## File-level result

All seven files advertised by the Zenodo API were present locally and matched
the API byte counts and MD5 checksums.  The record contains one documentation
PDF, five XLSX workbooks, and one CAD ZIP archive.  The XLSX workbooks expose
named wind/concentration cases and spatial grid summaries.  The ZIP contains
Inventor parts, assemblies, project files and lockfiles.

The recheck found no common elapsed-time plus measured-reservoir-pressure
column and no trace member that could provide the Figure 2 pressure-decay
curve's half-pressure crossing.  The existing 51-point digitized startup
segment remains the only numerical curve used by the archived Grune holdout;
it does not become eligible through this archive inspection.

## Decision boundary

`ARCHIVE_RECHECK_INELIGIBLE_FOR_GRUNE_PRESSURE_DECAY_HOLDOUT` is recorded in
[`grune_2014_archive_access_recheck_2026_10_05.json`](grune_2014_archive_access_recheck_2026_10_05.json).
The archive is useful for ventilation/concentration and geometry provenance,
but it cannot validate pressure decay, ignition, radiation, dispersion
distance, station controls, or SAGA effectiveness.  No model parameters or
readiness gates were changed as a result of this negative finding.
