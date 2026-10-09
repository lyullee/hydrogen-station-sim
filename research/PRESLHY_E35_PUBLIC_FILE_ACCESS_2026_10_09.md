# PRESLHY E3.5 public raw-file access audit (2026-10-09)

One workbook from the public PRESLHY E3.5 release was downloaded and checked without committing the raw file. The file contains five synchronized or near-synchronized channel families: release-source flow, pipe/nozzle pressure, thermocouples, hydrogen detector outputs, and local weather. Its SHA-256 and structural counts are recorded in [`preslhy_e35_public_file_access_2026_10_09.json`](preslhy_e35_public_file_access_2026_10_09.json).

This is useful evidence for controlled-release source reconstruction, detector logic, consequence visualization and incident replay. It is a liquid-hydrogen release experiment, so it cannot validate the gaseous HRS station-to-vehicle loop, cascade/compressor/precooler control or SAE J2601 filling. Because the workbook was accessed before a new prospective protocol was frozen, the audit remains a post-access diagnostic and does not change any validation gate.
