# Prospectively frozen MC Default external holdout

Generated: 2026-10-03T03:19:19.840833+00:00
Evaluation commit: `a147f58187a99b7331b0ac5a1f0e1ac2d62413b5`
Frozen model commit: `108f32553b56f151690a89ed2e0948c6f882a53e`
Archive SHA-256: `e029c53f95c8172be08e5dc4cc41dffb42a09ad7ecbb8b6b8d73e43a9ad210d1`

> The eight workbook outcomes were unopened when the protocol and case list were committed. No case-specific fitting, post-freeze parameter tuning, dynamic time warping or failed-case exclusion was permitted.

## Decision

Joint engineering-screen pass: 0/8 (0.0%).

The MC Default workbook schedule is represented by its endpoint-equivalent average pressure ramp because the frozen production controller accepts one constant APRR. This is a disclosed approximation and is not an implementation or certification of the proprietary MC Formula.

## Per-case results

| Case | Chamber | Effective APRR | P RMSE | T RMSE | Final SOC error | Screen |
|---|---:|---:|---:|---:|---:|---:|
| H2P-MC-1-A | 52.3 °C | 5.05 MPa/min | 12.44 MPa | 13.90 °C | -34.76 %p | FAIL |
| H2P-MC-1-B | 40.8 °C | 11.55 MPa/min | 14.90 MPa | 11.10 °C | -22.93 %p | FAIL |
| H2P-MC-1-C | 29.0 °C | 16.26 MPa/min | 13.73 MPa | 11.92 °C | -8.42 %p | FAIL |
| H2P-MC-1-D | 17.1 °C | 17.38 MPa/min | 14.10 MPa | 14.17 °C | -8.89 %p | FAIL |
| H2P-MC-1-E | 39.4 °C | 5.73 MPa/min | 19.47 MPa | 16.57 °C | -44.02 %p | FAIL |
| H2P-MC-1-F | 39.7 °C | 2.74 MPa/min | 22.66 MPa | 17.43 °C | -50.79 %p | FAIL |
| H2P-MC-2-A | 19.9 °C | 21.80 MPa/min | 11.92 MPa | 13.96 °C | -12.45 %p | FAIL |
| H2P-MC-9.8KG | 49.8 °C | 7.60 MPa/min | 17.68 MPa | 6.79 °C | -32.86 %p | FAIL |

## Scope

The experiment observes vehicle pressure, tank temperature, SOC, mass flow, inlet temperature and high-pressure source channels. It independently tests the frozen vehicle-fueling control, precooling and tank-response chain. The bench data do not expose all internal three-bank valve commands, so a passing result would not alone validate every station dispatch state or field safety.
