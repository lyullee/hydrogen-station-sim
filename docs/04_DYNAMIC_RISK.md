# Dynamic HyRAM Coupling

## Implemented interface

The process model now supplies HyRAM with an immutable release snapshot:

- absolute upstream pressure and temperature from CoolProp;
- physical or effective release diameter and discharge coefficient;
- release direction and consequence target coordinates;
- actual network mass flow for PRV and other modeled discharge connections;
- enclosure geometry, passive vent geometry, and forced ventilation rate.

Outdoor calculations use the actual network mass flow as an override for HyRAM
jet, flame, and overpressure models. This prevents a partially open PRV from being
treated as a fully open hole.

## Release-flow evidence range

Every free-orifice consequence result keeps the configured point calculation
and also reports `release_flow_lower_bound_kg_s` and
`release_flow_upper_bound_kg_s`. The additional range spans that point and the
aperture-specific P10--P90 effective-coefficient diagnostic from the independent
Proust 1--3 mm, approximately 10--90 MPa campaign. It exists because the frozen
single-coefficient transfer failed all three joint series screens; it is not a
post-outcome calibration. Results outside the public aperture, pressure, or
temperature domain are marked `PUBLIC_EXPERIMENT_ENVELOPE_EXTRAPOLATED`.

A `flow_limited_line` source preserves its declared process cap and reports
`PROCESS_FLOW_LIMIT_PRESERVED`; terminal-orifice evidence is not used to widen
a line/valve-controlled source. The range is a sensitivity screen rather than
a confidence interval, station measurement, consequence-distance validation,
or separation distance. The evidence and claim contract are recorded in
`research/RELEASE_FLOW_UNCERTAINTY_CONTRACT_2026_10_13.md`.

## Indoor accumulation

HyRAM+ 6.1 `analyze_accumulation` accepts an initial source state and volume,
orifice geometry, release position, enclosure dimensions, upper/lower vents,
forced ventilation, and requested times. It returns enclosure pressure, hydrogen
layer depth, hydrogen concentration, maximum overpressure, and release rate.

For an isolated tank leak, the coordinator starts a transient HyRAM session at
release onset and evaluates elapsed release time. For an operating discharge with
an externally calculated changing mass flow, the result is explicitly labeled
`orifice_model_not_actual_flow_override`: HyRAM's indoor API does not accept an
arbitrary mass-flow history, so that result is a scenario forecast rather than a
reconstruction of measured accumulation.

## Safety bridge

Hydrogen concentration trip thresholds are project configuration, not hard-coded
safety recommendations. `RiskToSafetyBridge` converts only explicitly configured
source/threshold pairs into external ESD reasons. The reasons can be passed to the
safety supervisor through `FaultInjection.external_trip_reasons`.

Gas-detector performance data should follow ISO 26142:2010, which covers range,
accuracy, response time, stability, selectivity, and poisoning for stationary
hydrogen detectors. <https://www.iso.org/standard/52319.html>

## References

1. HyRAM+ 6.1 and current Sandia documentation:
   <https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/>
2. HyRAM+ 6.0 Technical Reference Manual, SAND2025-04942:
   <https://doi.org/10.2172/2563814>
3. ISO/TS 15916:2026, basic hydrogen safety considerations:
   <https://www.iso.org/obp/ui#iso:std:iso:ts:15916:ed-1:v1:en>
4. H2Tools gaseous and liquid hydrogen fueling station best practices:
   <https://h2tools.org/bestpractices/gaseous-gh2-and-liquid-hydrogen-lh2-fueling-stations>

## Remaining limitations

- Multiple simultaneous indoor releases are evaluated independently; interaction
  between hydrogen layers requires a shared enclosure model or CFD.
- Sensor position within a stratified layer is not yet resolved.
- Vent-stack pressure loss and discharge direction are not yet connected.
- HyRAM execution is synchronous until the API worker layer is implemented.
- No alarm threshold or ventilation rate in this repository is a certified design
  value without the station SRS, enclosure drawings, and detector data sheets.
