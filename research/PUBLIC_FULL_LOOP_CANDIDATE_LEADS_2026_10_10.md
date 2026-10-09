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

The privacy-safe route is to request three de-identified events with a common
elapsed time, station/dispenser pressure, delivered-gas temperature, transferred
mass or mass flow, protocol phase, and (if available) vehicle/receptacle,
precooler, cascade and ESD channels. The request must freeze the protocol and
model before scoring and must not publish raw rows or facility identity.
