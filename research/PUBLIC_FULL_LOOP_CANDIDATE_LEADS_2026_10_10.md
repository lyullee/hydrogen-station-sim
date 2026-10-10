# Public full-loop data candidate leads

This record keeps public leads separate from admitted validation evidence. A
lead is not used for model fitting, scoring, or LLM claims until its raw data,
channel dictionary, synchronized time base, and reuse terms are independently
verified.

The BAM/KETI 2026 study is a high-value contact lead because it reports a
demonstration HRS with compressor, storage, dispenser, temperature and flow
measurements and a vehicle-refuelling test. The article and BAM description do
not provide a reproducible raw logger export in the current search, so it is
marked `CONTACT_REQUEST_CANDIDATE_ONLY`.

The NREL H2FillS trace remains useful but limited to a partial hose and
receiving-tank boundary. It is not a station-to-vehicle full-loop holdout.

The DLR railway-refuelling manuscript is another useful contact lead: it shows
real tank-module, dispenser pressure, temperature and mass-flow channels, but
the public material is a figure-level example rather than a downloadable,
clock-aligned logger archive. The European Hydrogen Observatory roster is
useful for pressure-class and station-layout context only; it contains no
process historian channels.

The Kuroki et al. 2021 station-to-vehicle model is a further high-value request
lead because it reports validation against an actual fueling station. The
publication does not itself expose a reproducible logger export or channel
dictionary, so it remains contact-only. [DOI](https://doi.org/10.1016/j.ijhydene.2021.04.037)

On 2026-10-10, the Kuroki DOI/institutional record and the DLR repository
record/manuscript were rechecked, including a targeted supplementary-data
search. The public records still expose validation context and plotted
measurements, not a downloadable synchronized logger with channel semantics
and reuse terms. This is a documented negative search result, not evidence that
the underlying custodians do not have the data.

The privacy-safe route is to request three de-identified events with a common
elapsed time, station/dispenser pressure, delivered-gas temperature, transferred
mass or mass flow, protocol phase, and (if available) vehicle/receptacle,
precooler, cascade and ESD channels. The request must freeze the protocol and
model before scoring and must not publish raw rows or facility identity.

For the BAM/KETI lead, the staged request text is in
[`BAM_KETI_DATA_REQUEST_DRAFT_2026_10_10.md`](BAM_KETI_DATA_REQUEST_DRAFT_2026_10_10.md).

These additional leads do not change the gate: no candidate is admitted as a
full-loop holdout until raw/de-identified rows, channel semantics, a common
clock, reuse terms and a pre-access frozen scoring protocol are all verified.
The 2023 Kuroki liner-temperature experiment is also recorded as a contact-only lead ([DOI](https://doi.org/10.1002/ente.202300239)). The publisher explicitly states that the research data are not shared, so its measured conditions remain contextual evidence and cannot be used as a full-loop holdout or fitting source.
