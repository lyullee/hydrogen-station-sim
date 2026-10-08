# DATA3632 seven-method HRS QRA comparison

This is a post-access descriptive inter-model comparison, not experimental validation.

- Files: **46**
- Methods: **7**
- Source rows retained: **211**
- Matched physical-input groups: **46**

## Overall consequence-distance envelopes

| Endpoint | n | Minimum | Median | Maximum |
|---|---:|---:|---:|---:|
| Direct 2.068 kPa overpressure distance | 82 | 28.646 | 64.030 | 307.551 |
| Direct 13.79 kPa overpressure distance | 82 | 13.624 | 28.557 | 77.436 |
| Interpolated 5 kPa overpressure distance | 82 | 20.271 | 43.976 | 161.821 |
| Direct 4 kW/m2 jet-fire distance | 125 | 0.929 | 11.054 | 37.131 |
| Direct 12.5 kW/m2 jet-fire distance | 122 | 1.092 | 8.534 | 28.032 |
| Interpolated 5 kW/m2 jet-fire distance | 122 | 1.148 | 10.508 | 35.142 |
| Direct exported jet-fire mass rate (kg/s) | 129 | 0.000 | 0.111 | 1.773 |

## Interpretation boundary

Across matched input groups, the method max/min distance ratio has median **1.000** and maximum **3.310**.

The range represents differences among implemented QRA methodologies. It is not an uncertainty interval, a safety factor, measured truth or a site-specific separation distance. Direct source endpoints remain distinguishable from the 5 kPa/5 kW/m2 log-log interpolations.

Claim boundary: The result measures variation among seven published QRA implementations for a common idealised HRS. The ensemble is not ground truth and cannot validate physical accuracy, accident frequency, site-specific separation distances, emergency actions, the station-to-vehicle dynamic loop or SAGA effectiveness.
