# Draft request: JHFC/NEDO six-run 35/70 MPa filling data

**Status:** draft only; no message has been sent.

## Purpose

Request the underlying measurements referenced by Monde et al., “Estimation of
temperature change in practical hydrogen pressure tanks being filled at high
pressures of 35 and 70 MPa”, *International Journal of Hydrogen Energy* 37
(2012), 5723–5734, DOI [10.1016/j.ijhydene.2011.12.136](https://doi.org/10.1016/j.ijhydene.2011.12.136).
The article describes six filling conditions from four practical tanks and
states that complete experimental data were opened for analysis.

## Requested files

1. The original timestamped files for all six runs, preferably CSV, XLSX or
   equivalent lossless export.
2. Vehicle-tank pressure and hydrogen temperature, station supplied pressure
   and temperature, mass-flow or transferred-mass channel if recorded, and
   fill start/stop markers.
3. Tank geometry/type, initial and final pressure/temperature/mass, gas
   pre-cooling condition, pressure-ramp or SAE/JHFC protocol information, and
   sensor locations.
4. Channel dictionary, units, sample interval/time zone, calibration dates,
   uncertainty, missing-value codes and quality flags.
5. Permission to publish derived, de-identified validation metrics and the
   file checksum in an open supplementary repository. Raw redistribution can be
   excluded if required; a controlled-access custodian and a reproducible
   scoring script are acceptable.

## Proposed independent validation use

The files would be preserved unchanged, hashed before inspection and split by
run under the repository's pre-access protocol freeze. They would be used only
as an independent tank/vehicle thermal validation holdout; no parameter fitting
would be performed after the files are opened. Any restrictions, corrections or
run exclusions would be recorded in the provenance manifest.

## Custodian leads

- Article authors and the JHFC/NEDO/JARI project archive:
  <https://www.jari.or.jp/jhfc/>
- Official paper DOI:
  <https://doi.org/10.1016/j.ijhydene.2011.12.136>

