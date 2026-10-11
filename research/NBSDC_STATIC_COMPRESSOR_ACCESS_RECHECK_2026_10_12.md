# NBSDC static-compressor access recheck (2026-10-12)

This live recheck records a high-value National Basic Science Data Center candidate for the paper: the catalogue describes static hydrogen compression, storage and supply performance tests and exposes a nested tree containing XLS/OPJU files for interstage supply, primary compression and final-stage delivery.

The official file-tree endpoints returned HTTP 200 and exposed names, sizes and node identifiers. A representative numerical XLS probe returned HTTP 200 with portal code **403** and the message that only selected description files can be downloaded and data files require a data-application process. No numerical bytes or cells were opened or persisted.

The candidate is therefore retained as a request lead and schema/context evidence only. It cannot be used for calibration, external scoring, station-to-vehicle claims, pressure/flow validation or IJHE quantitative claims until the custodian provides immutable files, channel definitions, units, time base, calibration/quality information and written permission for derived metrics and publication.

Sources: [NBSDC catalogue record](https://www.nbsdc.cn/general/dataDetail?id=64edc6babb16e07753c3461a&type=1), [NBSDC API/usage page](https://www.nbsdc.cn/general/openAPI).

The probe is reproducible with the endpoint recorded in the JSON artifact: `research/nbsdc_static_compressor_access_recheck_2026_10_12.json`.
