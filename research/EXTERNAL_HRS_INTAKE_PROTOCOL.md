# External HRS raw-data intake contract

This contract is the entry point for a future independent station-to-vehicle
validation package. It separates acquisition integrity from numerical
evaluation.

Before any row, cell, trace value or plot is inspected, the model commit,
eligibility rules and scoring implementation must be frozen. The intake script
only enumerates files and computes cryptographic hashes; it does not parse
measurements or calculate outcomes.

The minimum useful package must contain a common time base, vehicle or
receptacle pressure, gas/tank temperature, mass flow or transferred mass,
initial conditions, tank capacity, protocol mode, source/cascade state,
compressor and precooler state, stop/abort markers, units, quality flags and
calibration or uncertainty metadata. The declaration must also identify the
source, custodian/archive, UTC acquisition time and the licence or written
reuse reference. Missing fields are retained as an ineligibility reason rather
than silently imputed.

The manifest produced by `scripts/intake_external_hrs_bundle.py` is provenance
evidence only. It does not promote a dataset to a validation holdout. A later
evaluation must reference the manifest hash and a new, explicit prospective
protocol.

## Numerical trace-quality screen

The metadata contract requires the canonical units used by the frozen trace
screen: absolute pressure in `MPa_abs`, temperature in `degC`, and mass flow
in `g/s`. Gauge pressure or an unconverted alternate unit is rejected at
intake; conversion must be performed and documented before a new manifest is
created. This prevents a numerically plausible but physically mis-scaled trace
from entering the validation holdout.

After the metadata gate passes, `scripts/validate_external_hrs_trace.py` may
read only the explicitly mapped CSV trace. It applies the frozen row count,
missingness, monotonic-time, maximum-gap and physical-range checks in the
protocol. It performs no imputation, resampling, smoothing, model fitting or
outcome scoring. A quality-screen pass means that the trace is usable as an
input to the separately frozen numerical evaluator; it is not evidence that
the digital twin is accurate.

## Eligibility check after intake

The custodian may provide a separate metadata-only declaration based on the
template `research/external_hrs_bundle_declaration.example.json`. Run
`scripts/validate_external_hrs_manifest.py` with the intake manifest,
declaration and this protocol. The checker verifies the required channel names,
units, common time base, protocol metadata, freeze declaration, safe relative
paths, declared byte counts and SHA-256 values. It hashes quarantined bytes but
does not parse the data format or inspect a single measured value. A passing
decision means `ELIGIBLE_FOR_PROSPECTIVE_MAPPING` only. Numerical evaluation
still requires a separately frozen runner, untouched cases, locked scoring and
retention of every failed case.
