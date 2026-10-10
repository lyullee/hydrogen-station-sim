# Local long-form hydrogen archive recheck (2026-10-11)

This record screens one private, local long-form hydrogen-system export without
publishing its path, filename, site, company, manufacturer, calendar date,
channel names, identifiers, or raw rows. The committed JSON keeps only
aggregate counts and a coarse observation span.

The archive contains 2,410,985 measurement rows from 490 anonymized entities
and 273 anonymized key families over a 24-hour span. It has pressure,
temperature, flow/mass, hydrogen-process, and a small number of control-state
candidate families. These measurements are useful for station/component-side
diagnostics and operational context.

The screen does **not** open the independent HRS full-loop gate. A synchronized
receiving-vessel/vehicle trace and an attested station controller, cascade, and
ESD boundary were not established from the privacy-bounded aggregate. No
runtime parameter is changed and the readiness percentage is unchanged.

See `local_longform_hydrogen_archive_recheck_2026_10_11.json` for the machine-
readable, aggregate-only record.
