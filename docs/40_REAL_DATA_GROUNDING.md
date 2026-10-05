# Real-data grounding in runtime decision support

The simulator now carries a compact public-source index with each LLM evidence
header. The index is built only from evidence records that passed their local
provenance checks and contains a title, an inspectable URL, and the limited
purpose for which the source may be used. Current entries cover:

- NREL H2FillS and DOE/NREL high-flow fueling experiments for pressure, flow,
  temperature, and fill-duration operating-range context.
- The public HITRF facility description for storage tiers, compressor stages,
  and precooling scale context. It is not a synchronized logger archive.
- KHK public hydrogen-incident reports for qualitative scenario and response
  precedent.
- A licensed accidental-release dataset and an open detector-dispersion
  dataset for release/ignition wording and detector persistence replay.

The links are placed in `prompt_evidence_header()` and
`prompt_evidence_summary()` as `public_source_links`. This makes the sources
available to the main and sensor assistants without copying private rows into
the prompt. Private station logs remain represented only by de-identified
quality and calibration metadata; no operator, site, date, manufacturer,
tag, or raw row is exposed.

When a live frame contains a nozzle flow, the evidence envelope also adds
`public_operating_envelope_screen`. It compares the simulated flow with the
published high-flow experiment's aggregate average and peak and labels the
context as idle, below the heavy-duty average, within the reported context, or
above the reported peak. This label is explanatory only and is never used as
an accuracy score or as an automatic controller limit.

The source index does not change the numerical model or turn aggregate public
results into a holdout. The runtime must continue to describe the following
boundaries explicitly:

- `measured_boundary_calibration` is opt-in and currently changes only the
  station-bank recharge hysteresis.
- The private pressure replay supports a station-boundary plausibility check,
  not a station-to-vehicle validation.
- Public aggregate plots and facility ratings support operating-range and
  face-validity explanations, not ESD, controller, accident-frequency,
  consequence-distance, or field-certification claims.

The source list is intentionally deterministic and tested. A missing or
invalid source URL is omitted rather than replaced with an invented citation.
