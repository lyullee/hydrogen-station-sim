# ELVHYS 4.2 auxiliary replay

This record freezes a small, auditable subset of the public ELVHYS 4.2 data: all
three pressure-peaking tests (29–31), each with its pressure and flow-meter CSV.
The raw CSV files remain outside Git because the repository stores provenance and
hashes rather than redistributing the source archive.

- Source DOI: [10.18710/JXJP0H](https://doi.org/10.18710/JXJP0H)
- License: CC0 1.0
- Scope: a 1 m³ cryogenic hydrogen transfer-connection space, not a gaseous H70
  station-to-vehicle fueling loop.
- Files: six Dataverse file IDs, SHA-256 digests, timebase checks and channel
  summaries are in [`elvhys_auxiliary_replay.json`](elvhys_auxiliary_replay.json).

The replay confirms that the selected pressure and flow files are readable, have
strictly increasing common time bases, and contain the documented pressure-
peaking channels. The measured TCS pressure peaks increase across the three
vent configurations (approximately 6.2, 12.4 and 34.5 mbar on the higher
pressure channel). These are observations from the source data, not predictions
from the H70 model.

This is deliberately **not** a predictive validation gate. The outcomes were
accessed before this auxiliary record was frozen, no cryogenic enclosure model
was pre-registered, and the experiment does not contain vehicle pressure,
vehicle temperature, dispenser protocol state or station cascade/controller
telemetry. It therefore cannot close the full-loop external-validation gate or
the IJHE target for a validated H70 digital twin.
