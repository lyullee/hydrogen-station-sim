# HyTunnel-CS actual-hydrogen car-park holdout

## Outcome

The raw-time-series holdout completed on all 18 declared concentration cases
and all five declared blowdown mass-flow cases. No file, schema or runtime
failure remains in the final result.

Neither aggregate claim met its prospectively frozen screen:

| Endpoint | Eligible | Passed | Frozen aggregate rule | Result |
|---|---:|---:|---|---|
| Sensor-array-mean hydrogen concentration | 18 / 18 | 6 / 18 | all eligible and at least 70% pass | **FAIL** |
| Local 0.5 mm blowdown mass flow | 5 / 5 | 3 / 5 | all eligible and at least 4 pass | **FAIL** |

These negative results are retained. No case, physical parameter, metric,
acceptance threshold or aggregate decision was relaxed after outcome access.

## Concentration result

The zero-dimensional well-mixed model passed experiments 9--14. It failed the
remaining constant-flow cases and every blowdown case. The successful cases
show that a lumped balance can reproduce some enclosure-average responses, but
the 33.3% overall pass fraction is far below the frozen 70% requirement. The
model therefore cannot be used as a generally validated substitute for plume
geometry, stratification, detector placement, line dynamics or transient
source depletion in this enclosure.

The result directly narrows the next model-development target: a spatial or
multi-zone hydrogen transport model must be evaluated without fitting against
the same holdout. The failed aggregate result must remain the primary result
for this frozen model.

## Blowdown mass-flow result

The fixed `Cd = 0.8` real-gas aperture calculation reproduced the temporal
ordering closely in every case (`Spearman rho = 1.00`). Across the five cases,
NRMSE was 8.88--9.43% of measured peak and peak error was 18.57--19.72%.
Experiments 21--23 passed every frozen screen. Experiments 19 and 20 missed only
the median absolute percentage-error limit: 26.23% and 26.22% versus the frozen
25% maximum.

The predicted peak was systematically lower than measured (2.04--6.41 g/s
predicted versus 2.51--7.88 g/s measured). This supports the source model's
shape and pressure response as useful bounded evidence, but the fixed
discharge coefficient is not independently validated across all five cases.
Any future coefficient calibration must use a declared calibration subset and
a new untouched test split; it cannot revise this result.

## Execution disclosures

The protocol was committed before any raw MAT file was downloaded. Four
auditable stages are retained:

1. The first execution stopped before metrics because the archive uses MATLAB
   v7.3/HDF5. The original failure is preserved.
2. An HDF5 cell-reference loader was added without changing scientific rules.
3. The 1 kHz mass-flow and tank channels were reduced to deterministic
   one-second block means before the expensive real-gas calculation. This
   avoids electronic pseudoreplication and was frozen before a case metric
   completed.
4. Two documented schema repairs made tank channels optional for constant-flow
   experiments and applied the already declared stable duplicate-time rule to
   the common sensor time base. Intermediate failures are preserved.

The amendment artifacts state exactly which raw layout information had been
seen, which computations had completed, and which scientific decisions stayed
unchanged.

## Reproduction

Raw CC BY 4.0 MAT files are intentionally untracked. Download the declared
files from the dataset record, verify their checksums against the frozen
protocol and run:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\run_hytunnel_carpark_holdout.py `
  --data-directory <directory-containing-Exp04-through-Exp23>
```

- Dataset: <https://doi.org/10.23642/USN.14405903>
- Associated article: <https://doi.org/10.3390/en14113008>
- Frozen protocol: `research/hytunnel_carpark_holdout_protocol_2026_10_08.json`
- Final result: `research/hytunnel_carpark_holdout_result_2026_10_08.json`
- Raw files committed: **no**

## Claim boundary

This evidence concerns sensor-array-mean concentration in a mechanically
ventilated 60.8 m3 enclosure and local 0.5 mm blowdown mass flow from measured
upstream pressure and temperature. It does not validate local plume geometry,
detector placement, the 3.86 m line transient, outdoor HRS dispersion,
consequence distance, station controls, or a complete station-to-vehicle loop.
