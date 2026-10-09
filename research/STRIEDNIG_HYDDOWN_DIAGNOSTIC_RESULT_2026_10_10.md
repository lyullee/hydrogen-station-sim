# Striednig Type-I filling diagnostic (2026-10-10)

This record adds three publicly transcribed Type-I hydrogen filling experiments
from the HydDown validation archive to the vessel thermal evidence set. The
runner uses the source geometry, ambient condition, upstream pressure and
orifice boundary as supplied by the archive. It uses the project table-based
hydrogen properties and a mixed natural/forced gas-to-wall correlation, with no
case-specific fit.

## Result

| Case | Gas-temperature RMSE | Peak-temperature error | Predicted final pressure |
| --- | ---: | ---: | ---: |
| 5 MPa/min | 6.36 K | 4.34 K | 33.83 MPa(abs) |
| 10 MPa/min | 9.94 K | 1.89 K | 47.99 MPa(abs) |
| 30 MPa/min | 11.75 K | 2.88 K | 48.00 MPa(abs) |

The pressure and mass balances are numerically closed for all three runs. The
temperature errors are retained as diagnostic values; this is not promoted to a
prospective validation pass because the source arrays were already accessible,
the source is a secondary transcription, and the cases contain no station,
dispenser, controller, ESD or vehicle-side channels.

## Claim boundary

This evidence supports an additional independent check of the vessel thermal
submodel across Type-I filling rates. It does not validate station control,
cascade dispatch, dispenser metering, vehicle filling, emergency response or
consequence distances. It does not change runtime parameters or close the
station-to-vehicle full-loop gate. The original transcribed measurement rights
remain unresolved; only aggregate metrics and source hashes are retained here.
