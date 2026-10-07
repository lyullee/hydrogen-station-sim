# Validation data-acquisition tracker

This tracker records the next legitimate routes to obtain independent physical
hydrogen-refuelling data. It is deliberately conservative: a paper, plot,
summary endpoint, simulator output, data request or access lead is not counted
as validation. A candidate can enter an IJHE holdout only after the raw files,
rights, provenance, common time base, eligibility split and frozen model are
recorded before numerical outcomes are inspected.

The machine-readable tracker is [`validation_data_acquisition_tracker.json`](validation_data_acquisition_tracker.json).
The draft messages are retained under `research/*_DATA_REQUEST_DRAFT.md` and
must be reviewed and sent by the project owner. No message is sent by this
repository or by the audit script.

## Required evidence before a request can close a numerical gate

- synchronized machine-readable pressure and mass-flow/transferred-mass data;
- initial conditions, capacity, protocol/ramp metadata, units and quality flags;
- preferred fuel/vehicle temperature and station-controller state;
- a source digest and written reuse terms for derived metrics and repository
  deposit;
- a prospective freeze of eligible cases, implementation commit and error
  screens, with every eligible failure retained.

The tracker now includes one public synchronized physical-HRS archive, but its
status is `public_rows_received_post_access_mapping_incomplete`. This does not
permit goal completion. The existing negative full-loop result remains
authoritative until a genuinely independent event is mapped and frozen before
its numerical outcome is inspected.

## 2026-10-08 MetHyTrucks Hy-SaM intake

Three CC BY 4.0 ZBT workbooks were obtained from Zenodo and hash-verified. They
contain synchronized 0.5 s rows, and the flow integral agrees with the
cumulative-mass channel. A no-fit replay of the current public Type-IV tank
model retained all five mass-consistent candidate sessions. Case-mean RMSE was
1.287 MPa for pressure and 4.578 degC for temperature; all five met the
descriptive project screens. The result is recorded in
[`METHYTRUCKS_HYSAM_POSTACCESS_DIAGNOSTIC_2026_10_08.md`](METHYTRUCKS_HYSAM_POSTACCESS_DIAGNOSTIC_2026_10_08.md).

The archive was numerically inspected before this diagnostic protocol was
specified, and the public release lacks a channel dictionary, controller/bank
states and calibration metadata. It is therefore a post-access component
diagnostic, not a prospective full-loop holdout. The next request is narrowed
to those missing definitions plus a disjoint, previously uninspected event.

## 2026-10-06 access recheck

The catalogue file tree for a heavy-vehicle fast-refuelling dataset exposes
high-pressure hydrogen workbooks, low-pressure nitrogen traces, cylinder
temperature/flow tests and protocol documents. The numerical files still
require a data application; only the description file was downloadable without
login. The result is recorded in
[`nbsdc_heavy_vehicle_fast_refueling_access_recheck_2026_10_06.json`](nbsdc_heavy_vehicle_fast_refueling_access_recheck_2026_10_06.json).
The prepared request is
[`NBSDC_HEAVY_VEHICLE_FAST_REFUELING_DATA_REQUEST_DRAFT_2026_10_06.md`](NBSDC_HEAVY_VEHICLE_FAST_REFUELING_DATA_REQUEST_DRAFT_2026_10_06.md).
It is an acquisition lead and protocol/schema reference, not a scored holdout.
