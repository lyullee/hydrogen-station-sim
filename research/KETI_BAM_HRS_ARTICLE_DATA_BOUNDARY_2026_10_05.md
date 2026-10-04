# BAM/KETI HRS article: data-boundary record

The open-access article [Kim et al., *Data-Driven Intelligent Analysis System
for Monitoring and Anomaly Detection in Hydrogen Refueling Station*](https://doi.org/10.3390/app16157856)
reports field deployment at the BAM demonstration hydrogen refueling station
in Germany. It describes eight pressure, temperature and flow-rate sensors,
one-second acquisition and one-minute downsampling, and integration with a
remote safety-monitoring system.

The article is useful independent field context, but it is not a numerical
holdout for this repository. The public data-availability statement says that
the original contributions are included in the article and that further
inquiries should be directed to the authors; it does not publish a
downloadable, synchronized station-to-vehicle logger archive with a channel
dictionary, calibration uncertainty and raw-data reuse terms. Figures or
aggregate descriptions cannot substitute for the frozen full-loop channels
required by `research/RELEASE_NETWORK_PROSPECTIVE_PROTOCOL.md`.

The source is therefore recorded as a **real-station field-validation and data
request lead**. It must not be used to tune the locked model, report a new
holdout score or claim full-loop validation. A future request should ask for
de-identified event-level station pressure/temperature/mass-flow, receptacle
pressure/temperature, controller/protocol state, timestamps, calibration
metadata and publication reuse permission. The model and scoring protocol must
be frozen before any numerical outcomes are inspected.

Machine-readable record: `research/keti_bam_hrs_article_data_boundary_2026_10_05.json`.
