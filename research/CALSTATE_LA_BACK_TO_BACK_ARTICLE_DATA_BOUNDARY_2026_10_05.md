# Cal State LA back-to-back HRS article: data-boundary record

The paper [*Hydrogen station in situ back-to-back fueling data for design and
modeling*](https://doi.org/10.1016/j.jclepro.2021.129737) reports one year of
measurements at the Cal State LA Hydrogen Research and Fueling Facility. It
describes multiple daily fills, back-to-back events (less than five minutes
apart), storage pressure, dynamic cooling and temperature, fueling
thermodynamics, vehicle state of charge, and event frequency/duration.

This is useful real-station context, but it is not a public numerical holdout
for this repository. The publisher record is not open access and no
rights-cleared, downloadable synchronized station/dispenser/vehicle logger
archive with channel definitions and calibration uncertainty was found. The
paper's aggregate tables and plots cannot substitute for the frozen full-loop
channels required by `research/RELEASE_NETWORK_PROSPECTIVE_PROTOCOL.md`.

The source is therefore recorded as a **real-station operating and data-request
lead**. It must not be used to tune the locked model, report a new holdout
score, or claim vehicle-level validation. A future request should ask for
de-identified event-level pressure, temperature, mass-flow, storage and
controller state, vehicle/receptacle channels, calibration metadata, and
permission for derived publication and repository deposition.

Machine-readable record: `research/calstate_la_back_to_back_article_data_boundary_2026_10_05.json`.
