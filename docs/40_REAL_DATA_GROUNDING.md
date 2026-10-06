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
- The same USN/FFI concentration traces are also reduced to a robust
  22-case scale coefficient (`28.4495 vol% H₂ per g/s`). It replaces the old
  arbitrary `mass_flow × 10000` conversion in the advisory virtual detector.
  The coefficient is the median of each case's final-third, sensor-grid P90
  concentration divided by its measured mean release flow. Ventilation and
  wind factors remain separate, and concentrations are clipped to 100 vol%.
  This is a bounded open-channel proxy only; it is not an outdoor dispersion,
  detector-placement, ESD, or consequence-distance validation.

The links are placed in `prompt_evidence_header()` and
`prompt_evidence_summary()` as `public_source_links`. This makes the sources
available to the main and sensor assistants without copying private rows into
the prompt. Private station logs remain represented only by de-identified
quality and calibration metadata; no operator, site, date, manufacturer,
tag, or raw row is exposed.

Generated text is bounded a second time after the provider returns. The
`guard_llm_claims()` post-processor reads the same evidence manifest and
replaces positive claims of full-loop field validation, safety certification,
or a confirmed evacuation/safety distance when those gates are false. An
explicit limitation such as “this is not field validation” is preserved, as
are measured observations, calculated sample distances, and the staged
response plan. Each API answer exposes the small `llm_claim_guard` audit record
so a replay can show whether a provider overclaim was filtered.

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

The 2026-10-06 public-data recheck also inspected the 3Emotion operational-log
record, FCH2RAIL station/vehicle measurements, the FCH2RAIL KPI report, the
H2-Stations API, the IPCEI inventory and the open MetHyTrucks HySam
system-measurement record (Zenodo DOI `10.5281/zenodo.20590842`). HySam's
three CC BY 4.0 workbooks are verified against their published hashes and
provide 0.5 s instrumentation context, but their public metadata do not map
channels to a vehicle/receptacle or protocol state. These sources provide
real-station context or published curves, but no new rights-cleared
synchronized raw station-to-vehicle set. The search record is
`research/public_full_loop_search_recheck_2026_10_06.json`; its negative result
keeps the full-loop gate open rather than converting aggregate or plot-only
evidence into a validation claim.

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

The virtual detector alarm/trip rule is loaded from the hash-checked
`dispersion_detector_logic_validation.json` record when it is available. The
public replay covers 22 instrumented concentration cases using 1.0 vol% H₂
alarm, 2.0 vol% H₂ trip and 0.5 s persistence. Each live frame carries the
policy DOI, thresholds and claim boundary, so the LLM can distinguish a
publicly replayed detector rule from an outdoor detector-placement or ESD
validation. If the record is unavailable, the same values remain an explicit
fallback and the frame reports that provenance status.

The concentration scale is loaded from
`dispersion_concentration_proxy_calibration_2026_10_06.json`. Every HAZOP
frame exposes the artifact, DOI, coefficient, case count, formula and claim
boundary under `virtual_detector_proxy`; the LLM evidence manifest carries the
same record. If the derived artifact is missing, the recorded coefficient is
used only as a deterministic fallback and the status changes to
`PUBLIC_DISPERSION_PROXY_FALLBACK`.

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

The same public workbook also has a separate `public_geometry_sensitivity`
record. It compares the legacy effective volume with an opt-in capacity/EOS
geometry rule: the capacity/EOS variants screen 7/7 tanks, with mean pressure
RMSE of 3.54 MPa (frozen fit) or 0.50 MPa (no volume fit) and mean temperature
RMSE of 4.25--4.18 °C. These are post-access sensitivity results, so the
runtime keeps the existing `reference` default and the LLM labels the
capacity/EOS result as diagnostic only. Before changing a default, the rule
must be frozen before data access and evaluated on an untouched external
holdout.

An additional public HyTF trace is carried as `public_tank_trace_boundary`.
It contains 2,536 synchronized samples from a 70 MPa tank fill with two
pressure channels and fourteen tank thermocouples. Because it has no mass-flow,
vehicle/receptacle, station-controller or ESD channels, it is exposed as a
component-screen candidate only. Its repository commit and file hash are
retained for reproducibility, while raw rows remain outside the prompt and the
full-loop claim remains false.

Each simulation snapshot also carries the selected vehicle geometry basis and
declared capacities into the evidence envelope. This lets the main and sensor
assistants state whether the current run used the `reference` default or the
explicit `capacity_eos` option, instead of silently mixing a sensitivity run
with the default model.

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

The owner-controlled pressure bundle is also summarized by generic storage
role in `confidential_bank_role_pressure_envelopes_2026_10_06.json`. The
artifact keeps only medium/high role P05, median, P95, sampled-row counts and
pressure-ramp/restart-margin diagnostics. It excludes raw tags, site names,
dates and manufacturer information. The LLM receives this envelope so it can
compare a simulated bank pressure with a measured operating range, while
`runtime_parameter_application=false` keeps the evidence diagnostic-only.
The artifact does not attest temperature/flow roles, vehicle-side behavior,
field safety limits, consequence distances or full-loop validation.

The source list is intentionally deterministic and tested. A missing or
invalid source URL is omitted rather than replaced with an invented citation.
