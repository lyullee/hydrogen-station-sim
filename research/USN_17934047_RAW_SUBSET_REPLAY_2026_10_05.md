# USN 17934047 raw subset replay

This artifact replays three hash-identified MATLAB files from the public
DataverseNO record [10.23642/USN.17934047](https://doi.org/10.23642/USN.17934047),
marked CC BY 4.0.  The files are not copied into this repository; they remain
in the ignored local raw-data directory and are identified by the Dataverse
file ID, byte count and MD5 digest.

Each file exposes the documented `SIGMA` array with 999,999 rows and seven
columns (time, mass flow, Coriolis pressure and four thermocouples), together
with a three-column `GEN3i` array containing a time channel and overpressure.
The replay checks file identity, finite values, strictly increasing time bases,
channel shapes and observed ranges.  All three selected files pass these
integrity checks.

This is stronger raw consequence-component provenance than a summary-only
inventory, but it is intentionally not a model comparison.  The release
experiments do not contain the H70 station controller, cascade/precooler state,
dispenser protocol or vehicle-side loop required by the frozen full-loop gate.
They therefore cannot close full-loop validation or establish SAGA
effectiveness.  Any future consequence comparison must freeze its model and
inclusion rules before using the remaining raw files.
