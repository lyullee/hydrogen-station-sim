# MetHyTrucks Group D prospective transient protocol

This protocol freezes one public H70 vehicle-fill workbook before its numerical
contents are downloaded or opened. The selected file is
`20241024_Test_5_SINTEF_CESAME.xlsx` from Zenodo record
[`10.5281/zenodo.20590979`](https://doi.org/10.5281/zenodo.20590979), with the
publisher checksum and file size recorded in the machine-readable protocol.

The official MetHyTrucks D4 report identifies experiment 5 as an H70 vehicle
particulate-sampling fill. Its aggregate experiment descriptors were therefore
known before this freeze. Pressure, temperature and flow time-series values in
the selected workbook were not accessed. The result is prospectively frozen for
those transient outcomes, but it is not presented as fully blinded.

The exact workbook is retained even if it lacks a required channel, unit,
geometry field or usable time base. No alternative experiment may replace it
after access. The primary model comparison requires:

- a common monotonic time base;
- vehicle or receptacle pressure and gas temperature;
- mass flow or independently checkable transferred mass;
- delivered-gas temperature and upstream/nozzle pressure boundaries; and
- independently documented tank type and internal volume.

The model uses the already-frozen public Type-IV calibration without
case-specific fitting, signal smoothing or time warping. A primary PASS requires
pressure RMSE no greater than 5 MPa, temperature RMSE no greater than 10 C,
final pressure absolute error no greater than 5 MPa and peak-temperature
absolute error no greater than 10 C. Missing semantics or geometry produce a
retained ineligible result. Geometry is never inferred from an outcome.

This single event cannot close `full_loop_external_validation`, whose cohort
rule requires at least eight independent cases plus controller and station-state
evidence. It can add a genuinely pre-specified physical-HRS transient result and
prevent another post-access reinterpretation of public data.
