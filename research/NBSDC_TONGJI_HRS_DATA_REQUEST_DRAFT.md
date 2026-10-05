# NBSDC/Tongji liquid-hydrogen HRS data request

## Purpose

Request the machine-readable operational files listed in the public NBSDC record **液氢加氢站运行数据集** for independent validation of the hydrogen-station safety digital twin.

Public record: <https://nbsdc.cn/general/dataDetail?id=67d50e37195d260905af9869&type=1>

The record reports 16 hours of one-second station monitoring and lists 35 MPa dispensers, a 70 MPa dispenser, a 90 MPa compressor, high-pressure storage, and a liquid-hydrogen pump/tank system. The public file tree is visible, but the download endpoint requires a data application.

## Requested files

- `35MPa加氢机1.xlsx`
- `35MPa加氢机2.xlsx`
- `70MPa加氢机.csv`
- `90MPa压缩机.xlsx`
- `液氢泵-液氢储罐.xlsx`
- `高压储氢瓶组.xlsx`
- The channel/unit description and calibration or quality documentation.

## Minimum metadata

Please include the timestamp time zone, units, sensor/channel dictionary, tank and storage geometry or capacities, initial conditions, protocol or operating-step markers, sampling/dropout flags, calibration dates and any alarm, abort, maintenance or valve-state markers. Please identify which channels are measured directly and which are calculated conversions.

## Proposed validation use

The files would be quarantined on receipt. Before inspecting numerical outcomes, we would record the source response, file sizes and SHA-256 hashes, freeze the inclusion criteria and scoring code, and reserve an untouched holdout. The primary full-loop screen requires a common time base, pressure at the dispenser/receptacle or vehicle, and mass flow or transferred mass. We would retain every failed case and report the claim boundary.

## Rights request

Please confirm in writing whether the received files may be used for derived metrics, anonymised figures, an open reproducibility repository and an *International Journal of Hydrogen Energy* submission. Raw files can remain access-controlled if redistribution is not permitted; in that case we would publish hashes, schema, derived aggregates and the permission statement.

## Contact route

Use the NBSDC data-application route associated with record ID `67d50e37195d260905af9869`. Do not send this draft automatically; the project owner should confirm the institutional identity and the requested rights before dispatch.

## Public record recheck (2026-10-05)

The official record is [NBSDC dataset 67d50e37195d260905af9869](https://nbsdc.cn/general/dataDetail?id=67d50e37195d260905af9869&type=1), CSTR `16666.11.nbsdc.aI3fJrzX`, released 2023-03-21. Its public file tree lists six station data files: two 35 MPa dispenser workbooks, one 70 MPa dispenser CSV, a 90 MPa compressor workbook, a liquid-hydrogen pump/tank workbook, and a high-pressure storage-bank workbook. The downloadable description states that the records cover 16 hours at one-second resolution and are collected from actual station operation; it also states that the dataset is completely shared.

At the time of recheck, the six data-file endpoints returned an application-required response, while the description file was downloadable without login. Please provide the six original files or the authorized application route, preserving the native timestamps and all columns.
