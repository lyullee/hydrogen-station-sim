# Grune 2011 conference source recheck

Recorded on 2026-10-11 from the openly accessible [ICHs 2011 conference paper](https://conference.ing.unipi.it/ichs2011/papers/133.pdf), *Experimental study of ignited unsteady hydrogen releases from a high pressure reservoir* (Grune, Sempert, Kuznetsov, Jordan; KIT/Pro-Science). The paper is a conference source related to the later Grune journal work and is retained as a source-context artifact only.

## Source-reported release anchor

The paper describes a 0.37 dm³ high-pressure reservoir, initial pressures up to 200 bar, and 3, 4, and 10 mm release nozzles. For the 4 mm, 200 bar case, the text reports an average first-10-ms mass-flow rate of 66 g/s, a half-empty reservoir after 64 ms at approximately 100 bar, and a complete effusion time of roughly 500 ms. Figure 2 is a measured/calculated pressure-decay comparison; the published plot is not supplied here as a redistributable machine-readable trace.

These anchors are useful for diagnostics and for a future request for the underlying logger export. They are not a substitute for the measured Figure 2 time series: the published text does not provide enough points, uncertainty metadata, or a trace-specific machine-readable endpoint to satisfy the frozen Grune 2014 holdout protocol.

## Decision boundary

- `machine_readable_raw_pressure_trace_retrieved=false`
- `figure_2_full_curve_available_as_machine_data=false`
- `text_anchor_half_pressure_available=true`
- `numeric_holdout_added=false`
- `grune_2014_pressure_decay_gate_eligible=false`
- `model_promotion=false`

The 64 ms half-pressure and approximately 500 ms effusion values are retained as documented source anchors only. They must not be presented as an independent validation pass, a replacement for the frozen holdout, or evidence for station-scale safety distances, ignition outcomes, dispersion, or SAGA effectiveness. A future raw-data release would need independent episodes, native timestamps and pressure channels, calibration/uncertainty information, and a trace-specific source checksum before a new holdout is considered.

