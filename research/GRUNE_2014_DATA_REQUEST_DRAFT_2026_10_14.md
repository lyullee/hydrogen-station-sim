# Grüne 2014 pressure-trace data request draft

This draft requests only the minimum material needed to complete the frozen
pressure-decay holdout for the 0.37 L, approximately 20 MPa, 4 mm release in:

> Grune, J.; Sempert, K.; Kuznetsov, M.; Jordan, T. (2014), *Experimental
> study of ignited unsteady hydrogen releases from a high pressure reservoir*,
> International Journal of Hydrogen Energy, DOI
> [10.1016/j.ijhydene.2013.08.076](https://doi.org/10.1016/j.ijhydene.2013.08.076).

## Requested files

- The measured reservoir pressure trace for the 4 mm, approximately 200 bar
  case, including the complete discharge endpoint and any pre-trigger samples.
- Time and pressure columns with units, absolute/gauge basis, sampling interval,
  missing-value convention and the pressure-transducer range/accuracy.
- The initial vessel volume, initial gas temperature and any valve, rupture-disc,
  extension-tube or downstream-line dimensions needed to interpret the trace.
- A short event log identifying trigger time, valve-opening delay, acquisition
  start/stop and any clipping or rejected samples.

## Rights and provenance confirmation

Please state whether the supplied values may be used as derived coordinates in an
open scientific validation record and manuscript. The repository will retain a
cryptographic digest and derived metrics only unless redistribution of the raw
file is explicitly permitted. The source paper, authors, facility and DOI will
remain cited; no site, operator or confidential equipment information is needed.

## Locked evaluation boundary

The repository protocol is already frozen in
`research/grune_2014_holdout_protocol.json`. Numerical values must be delivered
before any model-parameter change or endpoint selection. The primary screens are
pressure NRMSE, median absolute percentage error and half-pressure timing. A
failed screen will remain a reported negative result; supplied data will not be
used to retune the runtime model.

Current public-access result: the KIT record and public paper copies expose
publication metadata and figure-level context, but no complete rights-cleared
machine-readable pressure-time trace has been found. See
`research/grune_2014_public_pressure_trace_recheck_2026_10_12.json`.
