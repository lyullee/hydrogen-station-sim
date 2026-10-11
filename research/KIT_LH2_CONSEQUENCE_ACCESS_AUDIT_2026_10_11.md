# KIT LH2 consequence archive access audit — 2026-10-11

The stage-1 protocol was frozen before any outcome file was opened. The local
The first local `archive.tar` was only 4,787,420 bytes and had MD5
`fb955817f010bc406669ab85e9c91887`. A session-aware retry received 964,689,920
bytes before the chunked HTTP stream ended; that partial file has MD5
`5dc3c9898487b08d273ee5b143840677`. Both differ from the public record's 5.0 GB
archive and MD5 `0e4ac934ecb973c6f07212e8a80707c9`. A header-only tar scan found
metadata and video member headers but ended with `unexpected end of data`.

No pressure, mass-flow, heat-flux, thermocouple or concentration values were
opened, no video outcome was viewed, and no model parameter was fitted. The
archive is therefore **not eligible for stage 2** and cannot be used as a
validation result. The next acquisition action is to obtain the exact archive
through an authenticated/session-aware download route, verify the publisher
checksum, and repeat the frozen member inventory before opening any outcome
file. A session probe confirmed that the landing page, download-terms endpoint
and temporary stream link respond successfully; the server returns a chunked
5.0 GB tar stream and did not honor a one-byte range request. Only 16 bytes were
read during that probe. The subsequent interrupted download is recorded in
`research/kit_lh2_download_attempt_2026_10_11.json`, and the access-path probe is
in `research/kit_lh2_session_access_probe_2026_10_11.json`.

The same session also exposed the RADAR BagIt backend archive endpoint. It
returned `206 Partial Content` with a complete `Content-Range` and a single
8-MB range was received successfully. Repeated range requests then reached the
server's `429 Too Many Requests` limit, so the range downloader is retained for
a slower, cooled-down retry: `scripts/fetch_kit_lh2_archive.py`. The range probe
does not change the integrity decision; the complete publisher MD5 is still
required before any outcome file can be opened.

The provenance and license lead remain the official [KIT RADAR record
10.35097/1483](https://doi.org/10.35097/1483), reported as CC BY-SA 4.0. The
machine-readable result is
`research/kit_lh2_consequence_access_audit_2026_10_11.json`.
