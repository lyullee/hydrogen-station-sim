# Confidential station-channel quality recheck

The owner-controlled archive was re-read using a custodian-supplied generic
mapping. The recheck retained only aggregate quality statistics. It did not
write source paths, filenames, tag names, timestamps, measured values or site
identifiers.

The sampled station-side logger window contained complete timestamp parsing and
finite pressure, flow, discrete-state and lifecycle observations for the
mapped channels. Temperature had one bounded missing fraction in the sampled
set. The timebase was monotonic for the sampled records, and discrete-state
transitions were counted without assigning undocumented meanings to the states.

This evidence supports a station-side data-quality and intake decision. It does
not attest engineering units or calibration, does not fit temperature/flow
parameters, and does not provide vehicle-side or full station-to-vehicle
validation. The measured pressure calibration therefore remains the only
runtime opt-in correction.
