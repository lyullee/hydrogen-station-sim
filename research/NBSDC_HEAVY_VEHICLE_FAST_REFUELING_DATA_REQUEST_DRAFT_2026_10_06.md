# Data request draft: de-identified fast-refuelling traces

**Subject:** Request for a de-identified numerical subset for independent hydrogen-refuelling model validation

We are preparing an academic validation study of a hydrogen-refuelling-station
safety digital twin. The public catalogue description indicates that the
dataset contains high-pressure hydrogen test-cylinder refuelling traces,
cylinder temperature, dispenser flow, protocol material and low-pressure
reference tests.

Could the custodian provide an approved, de-identified numerical subset for an
independent holdout? A CSV, Parquet or workbook export is sufficient. Please
omit operator, site, manufacturer, serial-number and exact-calendar-date
identifiers; a relative elapsed-time axis and opaque case IDs are sufficient.

## Minimum useful fields

- elapsed time and clock/sampling rule;
- test-cylinder or receptacle pressure and gas temperature;
- dispenser mass flow or cumulative transferred mass;
- initial pressure, volume/capacity and gas identity;
- protocol phase, target pressure, temperature limit and stop reason;
- units, calibration information, missing-value rules and quality flags.

## Reuse terms needed

Please confirm whether the project may compute and publish derived error
metrics, plots and de-identified aggregate tables, and whether a provenance
manifest and derived data may be deposited in an open repository. If only a
restricted review is permitted, the files will remain outside the repository
and will not be used as a public validation claim.

The evaluation protocol will be frozen before outcome columns are inspected.
No case-specific parameter fitting, time warping or selective case removal will
be performed; every eligible failure will be retained. Test-cylinder traces
will be treated as a component/protocol holdout unless the custodian confirms
their mapping to the vehicle-side validation contract.
