# Schefer 2007 public apparatus boundary — 2026-10-12

This record is a post-outcome boundary diagnostic for the frozen Schefer 2007 pressure-decay holdout. It does not alter the holdout, runtime parameters, or readiness counts.

## Publicly resolved

- Two storage tubes of approximately 617 L each were used for the blowdown campaign.
- The initial storage pressure was approximately 431 bar (about 41.3 MPa).
- The release nozzle was 5.08 mm in diameter.
- The reported two-tube blowdown lasted about 500–600 s and used a stagnation chamber before the exit.

## Still unresolved for a line-transient reconstruction

The public material reviewed here does not provide a rights-cleared common-clock raw file with the valve opening profile, upstream line volume or geometry, fitting/valve loss, and synchronized pressure/temperature/mass-flow channels. The apparatus therefore cannot be reconstructed sufficiently to validate a distributed line-inventory model without introducing unverified assumptions.

A related 2007 barrier-wall paper reports a 26.1 cm × 15.3 cm stagnation chamber and an approximately 2–3 s pneumatic-valve opening time for a tie-back test. Those values are useful candidate boundary clues, but the paper does not establish that they are the exact boundaries of the primary 617 L pressure-decay campaign. They are therefore not transferred into the frozen holdout or production model.

This is consistent with the existing frozen result: the well-mixed vessel model reproduces the initial pressure and approximate half-pressure time, but misses the early pointwise pressure shape. A line-volume/valve-opening explanation is plausible, but it is not a validated correction.

## Reproducibility boundary

The artifact is intentionally **diagnostic only**. It does not re-fit the Schefer 2007 trace, add a numeric holdout, promote a readiness gate, or change production behavior. A future line-transient validation must freeze a new untouched campaign before reading its outcomes and must include the missing boundary channels or equivalent documented parameters.

## Sources

- [Schefer et al. (2007), DOI 10.1016/j.ijhydene.2006.08.037](https://doi.org/10.1016/j.ijhydene.2006.08.037)
- [SAND2024-14886 public technical report](https://www.osti.gov/servlets/purl/2480221/)
- [Fundamentals of Hydrogen Safety Engineering I](https://www.arma.org.au/wp-content/uploads/2017/03/fundamentals-of-hydrogen-safety-engineering-i.pdf)
- [Schefer et al. (2009) related barrier-wall campaign](https://h2tools.org/sites/default/files/2019-08/paper_16.pdf)

Machine-readable record: `research/schefer_2007_public_apparatus_boundary_2026_10_12.json`.
