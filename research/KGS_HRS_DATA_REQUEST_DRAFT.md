# KGS HRS validation-data request draft

This draft is a request template only. It must not be sent automatically. The
paper and preprint report six real HRS fueling scenarios supplied by the Korea
Gas Safety Corporation, but the synchronized logger files are not included in
the public article or its open-source code release.

## Requested de-identified package

Please provide, for each eligible fill, a machine-readable export (CSV,
Parquet or XLSX) with a common timestamp and the original sampling interval:

- vehicle/receptacle pressure and vehicle-tank temperature;
- station, hose and dispenser pressure/temperature;
- instantaneous mass flow or cumulative transferred mass;
- storage-bank pressures and active-bank/cascade state;
- compressor, precooler, valve, stop and fault states;
- initial conditions, tank geometry/capacity and protocol/APRR settings;
- calibration, uncertainty, quality flags and missing-value conventions.

Please include the six scenario identifiers, units, time-zone/clock meaning,
sensor tag dictionary, data corrections already applied, and the exact
conditions used to classify normal and extreme fills. De-identify station and
vehicle identifiers while preserving the physical configuration needed for
replay.

## Rights and prospective-freeze requirements

The custodian should state whether the files and derived error tables may be
used in an open research repository and an International Journal of Hydrogen
Energy submission. On receipt, quarantine the package, record source, licence
and SHA-256 hashes, then freeze the model commit, inclusion rules and scoring
protocol before opening numerical outcomes. Missing required channels must make
the case ineligible for the primary claim; do not impute them.

## Source

- Oh et al., *Enhanced Thermofluidic Modeling and Open Source Rigorous
  Simulation of Hydrogen Fueling Systems Validated with Real-world Data*;
  published version: <https://doi.org/10.1007/s11814-025-00551-9>.
- Open preprint and stated CC BY 4.0 text: <https://doi.org/10.21203/rs.3.rs-6248350/v1>.

This request lead is not evidence of validation and cannot close the IJHE
readiness gate until an untouched raw package is received and prospectively
scored.
