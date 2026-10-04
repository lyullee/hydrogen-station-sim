# Public full-loop data search recheck

The independent full-loop validation gate requires a synchronized station-to-
vehicle fueling trace with pressure, mass transfer and documented initial and
protocol conditions, plus rights to publish derived metrics. The 2026-10-04
recheck retained the USN/FFI CC BY dataset as consequence/detector evidence,
but did not promote it to full-loop validation. H2FillS remains a
registration-gated simulator distribution, NREL retail products are aggregate,
MetHyTrucks is a sampling-system dataset, and the public HSR-Rig repository is
an unrelated metal-hydride reactor experiment.

No new eligible public raw full-loop set was identified. The next step is a
written data request for a de-identified logger export and reuse terms, followed
by a pre-access protocol freeze and independent holdout scoring.

The machine-readable decision record is
`public_full_loop_search_recheck_2026_10_04.json`. No restricted source file is
copied into the repository.

## National Basic Science Data Center access verification

The public [NBSDC record](https://www.nbsdc.cn/general/dataDetail?id=67fb63bb195d26544804482c&type=1)
was checked at file level. Its metadata identifies a Pucheng hydrogen station
engineering demonstration and advertises 17 files (30.07 MB),
including dispenser, storage-cylinder, unloading-column, compressor, sequence
control and alarm workbooks. The public file-tree API lists the files, but the
download endpoint returned a JSON `403` message stating that data files must be
obtained through a data application. The accompanying public description
document was downloadable and reports a 10-second sampling interval, a
2024-11-23--2024-11-27 collection window, and dispenser fields for nozzle
pressure, flow, inlet-gas temperature, dispensed mass and fill start/end
timestamps. No monitoring workbook was downloaded or inspected.

This is a high-value real-station acquisition route, not a holdout. The public
listing does not yet establish a scored synchronized vehicle/receptacle trace,
calibration/quality metadata, or reuse terms for derived publication. The
description hash, endpoint hashes and full file manifest are retained in
`nbsdc_hrss_operational_access_verification_2026_10_04.json`; a future request
must obtain a de-identified export, freeze the protocol/model before opening
outcomes, and record written permission for derived metrics and publication.
