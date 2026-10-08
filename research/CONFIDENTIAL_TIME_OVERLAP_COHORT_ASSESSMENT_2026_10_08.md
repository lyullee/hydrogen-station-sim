# Controlled station time-overlap cohort assessment

The privacy-bounded recheck screened 33 measurement-like CSV tables using only
bounded head/tail clock samples. All 33 tables exposed explicit absolute clocks.
The stricter interval test found 12 pairwise-compatible multi-table cohorts,
covering 24 unique tables, with at most three tables in one cohort. No file
name, source path, original header, timestamp, tag, measurement row, company,
location, manufacturer, or exact operating date is retained here.

Every cohort contains header-level time, pressure, mass-flow and
cascade/storage evidence. All 12 still lack controller-state, temperature and
vehicle channel families. Path-derived equipment hints close none of these
gaps. Consequently, the archive provides a useful shortlist for a controlled
station-side pressure--flow review after role/unit attestation, but it does not
contain a header-supported station-to-vehicle full-loop cohort.

This result supersedes clock-shape grouping for event discovery. The earlier
shape diagnostic grouped 26 tables into four sets because it intentionally
removed the absolute origin; equal record shape across different dates can
therefore look synchronized. It remains an intake diagnostic only. The new
overlap result does not itself attest common-event identity, units, calibration,
complete row alignment, vehicle state, model accuracy, or safety.

Next use is deliberately bounded: a custodian may map one of the 12 cohorts and
confirm units and physical-event identity for a station-side pressure--flow
diagnostic. A separate synchronized export containing vehicle pressure and
temperature, delivered mass/flow, station source state and controller/cascade
states is still required for full-loop validation.
