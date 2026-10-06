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

The current tracker status is `open_data_not_yet_received`. It does not change
the IJHE readiness audit or permit goal completion. The existing negative
full-loop, blowdown and high-pressure release results remain the authoritative
results until a genuinely independent dataset is received and frozen.

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
