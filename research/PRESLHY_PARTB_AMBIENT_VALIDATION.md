# PRESLHY Cryostat Part-B ambient holdout

This is an independent public-data holdout evaluation of the release and
source-inventory model. The protocol was committed before the RADAR archive
was downloaded or any numerical workbook was opened. The archive is the
PRESLHY Experiment series 3.1, part B, DOI `10.35097/1317` (KITopen DOI
`10.5445/IR/1000145859`), licensed CC BY-SA 4.0.

The claim is deliberately narrow: rigid-source pressure decay for the five
ambient-temperature Cryostat experiments. The published experiment report
describes a 225 dm³ Cryostat, a 0–250 bar(rel) pressure sensor, 2 mm and 4 mm
release nozzles, and a 6 bar(abs) vessel design limit. The evaluator uses
those reported quantities as inputs; it does not fit volume, discharge
coefficient, time alignment, or case-specific parameters.

## Frozen evaluation

- Protocol: `research/preslhy_partb_holdout_protocol.json`
- Runner: `scripts/run_preslhy_partb_validation.py`
- Archive SHA-256: `2d4fbc6b3d2996a40629c71c6a33a6fdec3fde246ee4cee23de12c86672cd4ff`
- Source volume: `0.225 m³` (reported Cryostat volume)
- Screens: pressure NRMSE ≤ 10%, half-initial-gauge-pressure time error ≤ 20%,
  and joint pass fraction ≥ 0.70.

## Result

The five eligible cases were all retained. Pressure NRMSE passed in all five
cases. The 4 mm cases passed the half-time screen, while both 2 mm cases were
too fast in the model (about 27% relative half-time error). The joint pass
fraction was **3/5 = 0.60**, below the frozen 0.70 threshold; therefore this
external validation claim is **not supported**.

| Case | Nozzle | Initial abs. pressure (bar) | Pressure NRMSE (%) | Half-time error (%) | Joint |
|---|---:|---:|---:|---:|---|
| W01 | 2 mm | 6.013 | 8.15 | 27.12 | FAIL |
| W02 | 2 mm | 4.163 | 9.03 | 27.13 | FAIL |
| W03 | 4 mm | 5.990 | 7.59 | 15.86 | PASS |
| W04 | 4 mm | 4.247 | 8.74 | 15.80 | PASS |
| W05 | 4 mm | 5.770 | 7.56 | 14.90 | PASS |

The result is retained as a negative result. It does not validate cryogenic
two-phase flow, ignition, dispersion, radiation, station control, refuelling,
or emergency separation distance. It also does not close the independent HRS
full-loop or SAGA human-factors gates.
