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
