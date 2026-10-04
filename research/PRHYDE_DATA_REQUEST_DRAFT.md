# PRHYDE / ZBT raw HRS-filling data request draft

## Provenance lead

The PRHYDE consortium's public D6.7 report describes ZBT 35/50/70 MPa
refueling tests, including Type-IV H70 vessels, pressure and temperature
measurements, upstream mass flow, and a 2 Hz central-PLC logging rate. The
report is an experimental provenance lead, not a machine-readable raw-log
release and not an untouched holdout for this project.

Public report: <https://lbst.de/wp-content/uploads/2023/04/PRHYDE_Deliverable-D6-7_Results_as_Input_for_Standardisation_V1-2_final_Apr_2023.pdf>

## Requested package

Please provide a de-identified export for complete fills and any associated
calibration/test-condition files. The preferred package contains:

- a common timestamp for vehicle/receptacle pressure, tank temperature,
  dispenser pressure, delivery temperature and mass flow or transferred mass;
- initial pressure, initial gas/tank temperature, ambient temperature, tank
  geometry/capacity and test identifier;
- pressure-ramp or PRHYDE/SAE protocol mode, target pressure/SOC and stop/abort
  reason;
- source pressure, precooler, compressor, valve and alarm states where
  available;
- units, sampling interval, sensor calibration/uncertainty and quality flags;
- written terms permitting derived error metrics, figures and a repository
  deposit, with the source files retained by the custodian if redistribution is
  restricted.

The package would be quarantined and byte-hashed before any numerical values
are inspected. Eligibility would be checked with
`scripts/validate_external_hrs_manifest.py`; a later prospective protocol
would freeze the model commit, case split and scoring rules before outcomes are
opened. A request, report table or digitized plot would not be counted as
full-loop validation.
