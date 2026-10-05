# H2Protocol capacity/EOS geometry diagnostic

This is a sensitivity report, not a confirmatory validation. It retains the
frozen global tank, flow and thermal parameters and changes only the vessel
volume basis:

```text
V = declared capacity / rho(P_nominal, 288.15 K)
```

The density is obtained from the tabulated Hydrogen EOS implementation. No
case-specific parameter was fitted and the production default was not changed.

| Quantity | Result |
|---|---:|
| Cases | 36 |
| Engineering-screening passes | 6 / 36 (16.7%) |
| Mean pressure RMSE | 5.836 MPa |
| Mean temperature RMSE | 10.804 °C |
| Mean SOC RMSE | 6.415 percentage points |

The declared-capacity geometry improves the diagnostic relative to the older
linear surrogate, but the aggregate errors still exceed the project screening
limits. It therefore does not close the IJHE validation gate and must not be
presented as a validated production-model update. A new protocol would need to
freeze the geometry rule before any prospective re-evaluation.

Machine-readable details are in
`research/h2protocol_capacity_geometry_diagnostic_2026_10_05.json`.

