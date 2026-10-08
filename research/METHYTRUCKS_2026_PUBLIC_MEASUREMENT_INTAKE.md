# MetHyTrucks 2026 public measurement intake

This audit covers all three public sampling-system releases available from the
MetHyTrucks Zenodo community. Raw workbooks remain outside version control.

## Result

- Integrity status: **PASS**
- Public records: **3**
- Workbooks: **15**
- Synchronized samples: **58,440**
- Sampling interval(s): **0.5 s**
- Workbooks with a mass channel: **6**
- Detected transfer sessions: **18**
- Sessions with a non-zero scale change and therefore eligible for closure comparison: **9**
- Descriptive flow/mass closure screens passed: **8 / 9 comparable sessions**
- Sessions without a measurable scale change (not scored): **9**
- Median flow/scale ratio across comparable sessions: **1.003**
- Median absolute relative flow/scale difference: **0.48%**

## Source records

| Group | DOI | Workbooks | License |
|---|---|---:|---|
| Group A -- NPL system measurement data | [10.5281/zenodo.20590761](https://doi.org/10.5281/zenodo.20590761) | 10 | cc-by-4.0 |
| Group B -- HySam system measurement data | [10.5281/zenodo.20590842](https://doi.org/10.5281/zenodo.20590842) | 3 | cc-by-4.0 |
| Group C -- ENGIE system measurement data | [10.5281/zenodo.20590903](https://doi.org/10.5281/zenodo.20590903) | 2 | cc-by-4.0 |

The operating-context check used the public
[D1 -- Good practice guide on HD-HRS parameters for representative and reliable sampling (e.g. gaseous and particulate phases)](https://doi.org/10.5281/zenodo.20540258).
The physical test-class check used the public
[D3 -- Report on the development of four reference methods/systems including implementation of sampling systems for hydrogen quality assessment](https://doi.org/10.5281/zenodo.18185068).

## Scientific use

The archive materially strengthens provenance for real HRS sampling-system
pressure, temperature, flow and transferred-mass behavior. The flow/mass
closure calculation is a post-access component diagnostic and records every
passing and failing session.

D3 resolves Groups A and C as 35 MPa direct/serial sampling-system tests
fed from medium-pressure station banks; the documented sinks are sampling
hardware rather than vehicle tanks. It does not close the station-to-vehicle
full-loop gate. The release also does not
contain an authoritative channel/unit dictionary, an explicit workbook-to-device
crosswalk, vehicle tank geometry, controller/bank/valve states or calibration
uncertainties. D1 provides operating guidance but does not fill those metadata gaps.

## Claim boundary

The 15 CC BY 4.0 workbooks are real public experimental traces and can support post-access component diagnostics, including descriptive flow-to-scale mass closure. D3 identifies Groups A and C as 35 MPa direct/serial sampling-system tests, not vehicle-tank filling traces. Outcomes were inspected before this audit and the release lacks an authoritative tag/unit dictionary, vehicle geometry and station controller states. It therefore does not establish prospective validation, a complete HRS-to-vehicle full-loop result, safety performance or regulatory compliance.
