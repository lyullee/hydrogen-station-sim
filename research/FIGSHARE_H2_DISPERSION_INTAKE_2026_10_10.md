# Figshare open-channel hydrogen-dispersion intake

The public Figshare record [10.23642/USN.26117989.v2](https://doi.org/10.23642/usn.26117989.v2)
contains 22 experiment ZIP files and a readme under a CC BY 4.0 licence.  The
files contain temporal mass flow, filling pressure and 29 hydrogen-concentration
channels in an open-ended rectangular channel.  The associated geometry paper
reports a 5.8 m × 0.9 m × 0.8 m channel, a 4.6 mm ceiling inlet and 29 sensors
([10.1016/j.ijhydene.2024.10.038](https://doi.org/10.1016/j.ijhydene.2024.10.038)).

`scripts/intake_figshare_h2_dispersion.py` retrieves the API manifest and can
audit locally downloaded ZIP files.  It checks archive hashes when available,
detects the CSV header, counts sensor channels, and checks the flow and sensor
time bases for monotonicity.  Raw rows remain outside the repository; only the
manifest and derived schema summary are committed in
`figshare_h2_dispersion_intake_2026_10_10.json`.

The current intake is a **dispersion-component holdout candidate**, not an HRS
full-loop validation.  It has no station controller, cascade, dispenser,
vehicle/receptacle, ESD, or outdoor consequence-distance channels.  It must
therefore not change the full-loop gate, runtime parameters, or safety-distance
claims.  A spatial screen must be frozen before scoring the locally available
cases; any fitted or outcome-dependent model remains development-only.

All 22 local ZIP files were size-checked against the API manifest and their
CSV schemas were read without publishing raw rows.  The checked T00014
exemplar contains 29 sensor columns, a monotonic 187.9 s flow timebase, 505
rows with sensor observations, and a maximum recorded mass flow of 0.0416 g/s.
Figshare does not expose MD5 values for these files in the API response, so
the local SHA-256 values are retained and the API checksum comparison is
explicitly marked unavailable.
