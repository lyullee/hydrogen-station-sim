# Independent 90 MPa release holdout protocol

This protocol was frozen before numerical values were read from the figures in
Proust, Jamois and Studer, *High pressure hydrogen fires*, DOI
`10.1016/j.ijhydene.2010.04.055`.

The experiment is valuable because it used a separate French facility, a 25 L
Type-IV source near 90 MPa, and 1–3 mm terminal orifices. The primary test is
limited to the already-developed real-gas aperture mass-flow relation at measured
pressure and temperature. It does not test the flame, radiation, vessel wall,
long supply line, or station layout.

## Frozen decision

- Each nozzle-diameter series needs at least eight jointly mappable measured
  pressure, temperature and mass-flow states between 2 and 95 MPa absolute.
- All three 1, 2 and 3 mm groups are required.
- A series passes only when mass-flow NRMSE is at most 15% of measured peak and
  median absolute percentage error is at most 20%.
- The claim requires at least two of the three series to pass.
- Missing measured temperature cannot be replaced with ambient temperature.
- Every readable state and every eligible calculation failure is retained.

Two independent digitization passes, axis-resolution uncertainty and the exact
source figure are recorded before model predictions are computed. If the paper
does not expose enough jointly mappable data, the result is ineligible rather
than repaired after inspection.

The public conference PDF has no identified data-redistribution licence. It is
kept outside Git; the repository stores citation, extraction provenance and
derived validation evidence only.
