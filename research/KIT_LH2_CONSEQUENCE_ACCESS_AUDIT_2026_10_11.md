# KIT LH2 consequence archive access audit — 2026-10-11

The stage-1 protocol was frozen before any outcome file was opened. The local
`archive.tar` is only 4,787,420 bytes and has MD5
`fb955817f010bc406669ab85e9c91887`, whereas the public record reports a 5.0 GB
archive with MD5 `0e4ac934ecb973c6f07212e8a80707c9`. A header-only tar scan found
one directory and one incomplete video member and ended with `unexpected end of
data`.

No pressure, mass-flow, heat-flux, thermocouple or concentration values were
opened, no video outcome was viewed, and no model parameter was fitted. The
archive is therefore **not eligible for stage 2** and cannot be used as a
validation result. The next acquisition action is to obtain the exact archive
through an authenticated/session-aware download route, verify the publisher
checksum, and repeat the frozen member inventory before opening any outcome
file. A session probe confirmed that the landing page, download-terms endpoint
and temporary stream link respond successfully; the server returns a chunked
5.0 GB tar stream and did not honor a one-byte range request. Only 16 bytes were
read during the probe. The probe is recorded in
`research/kit_lh2_session_access_probe_2026_10_11.json`.

The provenance and license lead remain the official [KIT RADAR record
10.35097/1483](https://doi.org/10.35097/1483), reported as CC BY-SA 4.0. The
machine-readable result is
`research/kit_lh2_consequence_access_audit_2026_10_11.json`.
