# Local measured boundary replay

An anonymized station pressure boundary from the current local bundle was injected into the reference station model using the controlled replay runner. The trace was selected by signal-only maximum absolute pressure ramp; no simulated outcome was used to choose the window.

The replay used a bounded 300-second window with a 0.2-second control period. It completed 1,501 samples without an ESD trip. The input was pressure-boundary-only because the current trace does not carry an attested vehicle pressure/temperature/mass or SOC channel.

This is a real data-to-model integration check for the station boundary. It is retained separately from the frozen operational-envelope profile because the current trace aggregate has a different time span and sampling interval. The runtime profile is not replaced automatically.

Raw source rows, source paths, dates, tag names, site identity, and manufacturer information are not stored in the report.

## Interpretation

The replay confirms that the acquired station-side data can exercise the simulator’s pressure boundary and protection-aware solver. It does not validate the complete station-to-vehicle loop, dispenser protocol accuracy, consequence distances, or field safety.
