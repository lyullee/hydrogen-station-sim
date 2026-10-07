# Controlled, frozen HRS full-loop evaluation

This workflow converts an authorised, de-identified controlled trace into a
reproducible **evaluation**, without copying raw station records, tags,
locations, manufacturer information, or absolute timestamps into this
repository. It is deliberately not a model-fitting route and it cannot turn a
station-boundary-only log into a vehicle-fill validation claim.

## What it answers

For a single recorded event, it compares the existing process model at one
specific Git commit with the observed vehicle pressure, vehicle temperature,
mass flow, delivered-gas temperature, and selected cascade-source pressure.
With all three cascade-bank pressure channels, it also evaluates cascade-bank
pressure trajectories, selected-bank agreement, and compressor-active state.

The evaluator produces aggregate error metrics and pass/fail checks only. It
does not persist raw rows. A pass is a bounded comparison at the stated
operating point, not a safety certificate, site acceptance result, or general
claim of model validity.

## Evidence scopes

| Receipt scope | What can be evaluated | What cannot be claimed |
|---|---|---|
| `station_to_vehicle_selected_bank_only` | Vehicle boundary, selected source pressure, temperature and flow | Cascade dispatch/recharge model validation; unmeasured bank trajectories must not be inferred |
| `cascade_resolved_station_to_vehicle` | The above, plus all three bank trajectories, selected-bank state, and compressor-active state | Any variable not measured/attested in the trace |

The controlled exporters attach this scope to their receipt. The evaluator
rejects a scope mismatch and refuses to interpolate a missing bank channel.

## Custodian workflow

All example paths below point **outside** this repository. Keep the trace,
receipt, draft protocol, approved protocol and result in the controlled
workspace.

1. Create the de-identified trace and receipt with the controlled exporter.
2. Create an external protocol draft without reading the trace rows:

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe scripts\prepare_controlled_full_loop_evaluation.py `
  --receipt D:\controlled\case-001\receipt.json `
  --output D:\controlled\case-001\frozen-protocol-draft.json
```

3. The authorised custodian fills every `null` field from approved pre-outcome
   operation records: vehicle internal volume and nominal pressure, command
   target/ramp, gas temperature and flow limits, ambient condition, all three
   initial bank pressures, trailer boundary values, and literal state mappings.
   The hash-locked trace's first vehicle pressure/temperature sample is the
   declared initial state (`vehicle.initial_state_policy` is fixed to
   `trace_first_sample`). The owner selects acceptance limits before seeing
   evaluator metrics.
4. The custodian records the freeze decision in the controlled study record,
   sets `frozen_before_outcomes` to `true`, and leaves the trace unchanged.
   The `expected_trace_sha256` must not be edited.
5. Check out the exact `model_commit` in the protocol and make the source
   worktree clean. Run:

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe scripts\evaluate_controlled_full_loop.py `
  --trace D:\controlled\case-001\full_loop_event.csv `
  --receipt D:\controlled\case-001\receipt.json `
  --protocol D:\controlled\case-001\frozen-protocol.json `
  --output D:\controlled\case-001\evaluation-result.json
```

The command refuses inputs inside the Git worktree, trace-hash substitution,
an unclean source worktree, a changed model commit, a non-frozen protocol, an
unsupported evidence scope, and incomplete canonical fields.

## Outcome reporting

The result records SHA-256 digests, source commit, scope, aggregate RMSE/MAE
and final/max errors, state-match accuracy, thresholds and each criterion's
pass/fail decision. Report the scope and the failure count, not only a pass.
For publication, disclose that source identifiers, absolute timestamps and raw
rows remain controlled; state the sampling/quality screen, frozen protocol
policy and all observed boundary definitions.

Do not retune the model after a failed frozen evaluation and call the result a
holdout. Use a new, separately frozen protocol and declare the new experiment
as a calibration or sensitivity study.

## Complete-cohort registry

A single passing event cannot close the full-loop evidence gate. Before case
outcomes are generated, collect the receipts for every planned independent
event and create one external cohort protocol:

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe scripts\prepare_controlled_full_loop_cohort.py `
  --receipts D:\controlled\case-*\receipt.json `
  --output D:\controlled\cohort\cohort-protocol-draft.json
```

The custodian must retain at least eight unique traces, fill the same
individual criteria used by every case protocol, attest independence/blinding/
controlled-use rights, retain the 80% or higher cohort pass criterion, and
freeze the cohort before reading any case result. Failed and incomplete cases
must remain in the cohort.

After every case has one result, generate a random secret file of at least 32
bytes and keep it outside the repository. Build the privacy-bounded registry:

```powershell
.\.venv\Scripts\python.exe scripts\build_controlled_full_loop_registry.py `
  --protocol D:\controlled\cohort\cohort-protocol.json `
  --results D:\controlled\case-*\evaluation-result.json `
  --salt-file D:\controlled\cohort\registry-secret.bin `
  --output D:\controlled\cohort\cohort-registry.json
```

The registry refuses missing, substituted or duplicate cases; mixed scopes,
commits, metrics or acceptance limits; and unsafe privacy declarations. It
publishes cohort-local HMAC codes instead of trace/result hashes, retains every
failure, and separates numerical-screen success from independent-holdout
provenance. The secret salt must never be committed or shared with the public
registry.
