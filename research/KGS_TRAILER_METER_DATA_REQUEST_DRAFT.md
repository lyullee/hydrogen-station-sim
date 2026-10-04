# KGS-linked tube-trailer metering data request draft

This is a request template only. It must not be sent automatically. The
published paper documents a real component-level tube-trailer supply and
transaction-volume metering experiment, including pressure, temperature,
Coriolis mass-flow measurement and 1 Hz acquisition, but the public article
does not provide the synchronized raw rows needed for an untouched full-loop
holdout.

## Requested de-identified package

For each experiment, please provide a machine-readable export (CSV, Parquet or
XLSX) containing:

- a common timestamp and original sampling interval;
- upstream/downstream pressure and gas temperature;
- instantaneous mass flow and cumulative transferred mass;
- tube-trailer geometry, initial inventory and boundary conditions;
- valve/controller state, stop command and fault markers;
- reference-scale readings, calibration certificates and uncertainty;
- sensor tag dictionary, units, clock meaning, quality flags and missing-value
  conventions.

Please preserve the experiment identifiers and physical configuration while
de-identifying site and vehicle identifiers. Describe any filtering,
resampling, sensor correction or mass-balance adjustment already applied.

## Rights and prospective freeze

Please state whether the files and derived error tables may be deposited in an
open research repository and used in an *International Journal of Hydrogen
Energy* submission. On receipt, quarantine the package, record provenance,
licence and SHA-256 hashes, then freeze the model commit, inclusion rules and
scoring protocol before opening numerical outcomes. Missing required channels
make a case ineligible for the primary full-loop claim; do not impute them.

## Source

- *수소충전소 계량 정확도 향상을 위한 거래량 산출 모델 연구*,
  DOI [10.7316/KHNES.2022.33.6.692](https://doi.org/10.7316/KHNES.2022.33.6.692).
- Public article page:
  <https://journal.hydrogen.or.kr/_common/do.php?a=full&aidx=35162&b=52&bidx=3154>.

This request lead is not validation evidence and cannot close the IJHE
readiness gate until an untouched raw package is received and prospectively
scored.
