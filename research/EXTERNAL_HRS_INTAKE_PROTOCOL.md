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
calibration or uncertainty metadata. Missing fields are retained as an
ineligibility reason rather than silently imputed.

The manifest produced by `scripts/intake_external_hrs_bundle.py` is provenance
evidence only. It does not promote a dataset to a validation holdout. A later
evaluation must reference the manifest hash and a new, explicit prospective
protocol.
