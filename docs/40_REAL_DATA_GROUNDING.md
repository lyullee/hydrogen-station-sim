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
- The public Grune/Sempert confined-space ventilation archive. Its 42 measured
  spatial profiles are reduced to no-wind-normalized factors by release size,
  flow and wind mode. These factors are applied only to the virtual detector
  proxy; they are not used as a CFD field, detector-placement certification or
  station-scale validation.

The links are placed in `prompt_evidence_header()` and
`prompt_evidence_summary()` as `public_source_links`. This makes the sources
available to the main and sensor assistants without copying private rows into
the prompt. Private station logs remain represented only by de-identified
quality and calibration metadata; no operator, site, date, manufacturer,
tag, or raw row is exposed.

The private schema intake also carries a privacy-bounded family summary for
compressor/station pressure and temperature, flow/totalizer, valve/alarm and
lifecycle channels. The current archive contains zero vehicle-side channel
families, so the assistant keeps station-boundary calibration separate from
vehicle-fill or station-to-vehicle accuracy claims.

The pressure bundle is also summarized by generic channel index. Its two
measured boundary channels have distinct operating envelopes, which is useful
context for the assistant when explaining a bank-specific observation. The
channel-to-bank mapping is withheld and remains unattested in the public
artifact, so these values are diagnostic evidence only and do not retune the
controller automatically.

When a live frame contains a nozzle flow, the evidence envelope also adds
`public_operating_envelope_screen`. It compares the simulated flow with the
published high-flow experiment's aggregate average and peak and labels the
context as idle, below the heavy-duty average, within the reported context, or
above the reported peak. This label is explanatory only and is never used as
an accuracy score or as an automatic controller limit.

The source index does not change the numerical model or turn aggregate public
results into a holdout. The runtime must continue to describe the following
boundaries explicitly:

The Grune-derived envelope is the one bounded exception: it changes the
virtual detector concentration proxy when leak flow, orifice size and wind
direction are available. The factor is nearest-neighbour/interpolated only
inside the measured diameter/flow/mode envelope and falls back to `1.0` for
unrepresented conditions. During an active release the runtime defaults to the
measured upper spatial envelope (`max(median, p90/no-wind-p90)`) so a local
high-concentration point is not hidden by a spatial median. The central
estimate remains selectable for sensitivity runs. This is a conservative
detector-proxy choice, not a detector-placement or outdoor-dispersion claim.
The evidence header exposes the DOI, profile count, factor count, statistic,
and claim boundary so an LLM cannot present it as full-loop validation.

The public Cal State LA back-to-back fueling article is also included as
real-station operating context. It reports multiple daily and back-to-back
fills together with storage pressure, cooling/temperature, thermodynamic and
vehicle-SOC outputs. The public record does not provide a reusable synchronized
row-level archive, so the LLM may use it for scenario and face-validity
context, while the full-loop validation gate remains closed.

The NREL H2FillS HDVS Type-IV workbook is evaluated separately as a frozen
tank/thermal boundary screen. It contains seven tanks and 351 synchronized
samples with measured pressure, temperature and mass channels. The current
model screen reports pressure RMSE 6.16 MPa, temperature RMSE 4.62 °C and
zero of seven tanks passing the predeclared joint screen; the measured-to-model
EOS-equivalent volume ratio is about 0.91. That ratio is a geometry diagnostic,
not a fitted production correction. The workbook remains local and ignored;
only the aggregate result is exposed to the LLM through
`public_tank_validation_boundary`, with a claim boundary that excludes
station-controller, receptacle and full-loop validation.

- `measured_boundary_calibration` is opt-in. It applies the de-identified
  station-boundary pressure margin to both cascade dispatch and recharge
  restart selection, so a bank is not repeatedly selected around the measured
  pressure noise band. It does not alter vehicle geometry, temperature or flow
  parameters because those channel roles are not attested in the private
  aggregate.
- When this profile is active, each operator frame also carries a
  `measured_boundary_envelope` scope diagnostic for the simulated source
  pressure. It reports whether that value is inside or outside the observed
  range and the distance to the nearest observed limit. This is an evidence
  boundary check only; it is not a safety limit, trip criterion, bank mapping,
  or vehicle-side validation.
- The private pressure replay supports a station-boundary plausibility check,
  not a station-to-vehicle validation.
- Public aggregate plots and facility ratings support operating-range and
  face-validity explanations, not ESD, controller, accident-frequency,
  consequence-distance, or field-certification claims.

The source list is intentionally deterministic and tested. A missing or
invalid source URL is omitted rather than replaced with an invented citation.
