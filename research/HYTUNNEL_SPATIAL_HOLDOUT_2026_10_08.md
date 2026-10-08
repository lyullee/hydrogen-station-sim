# HyTunnel actual-hydrogen spatial-rank holdout

## Outcome

The exact orientation-class detector rank candidate frozen during earlier
H2SAFE development was evaluated on sensor coordinates and per-sensor hydrogen
responses from 18 HyTunnel experiments. All 18 declared cases were eligible
and the final execution had no missing-file, schema or runtime failure.

The joint screen **did not pass**. Three of four aggregate criteria passed:

| Frozen screen | Result | Limit | Pass |
|---|---:|---:|---|
| Median Spearman rank correlation | 0.560 | >= 0.500 | yes |
| Cases with Spearman >= 0.4 | 83.3% | >= 60.0% | yes |
| Mean top-five recall of observed response quartile | 0.578 | >= 0.600 | **no** |
| Highest-scored sensor in observed response quartile | 94.4% | >= 70.0% | yes |

The failed top-five recall result is 0.022 below the frozen threshold. The
threshold was not relaxed and no case was removed. The candidate therefore
remains disabled for runtime detector routing.

## Interpretation

This independent actual-hydrogen result is materially stronger than the prior
post-access six-sensor diagnostic. It shows that the frozen geometry model
usually identifies at least one highly exposed detector and preserves useful
rank ordering across changing release and ventilation conditions. It does not
consistently recover enough of the full high-response sensor quartile in its
five highest predictions.

The remaining error is consistent with physics omitted by the candidate:

- forced-ventilation direction and velocity;
- the downward near-field jet before buoyant rise;
- the table/vehicle obstruction and split plume paths;
- enclosure boundaries and recirculation;
- time-dependent source strength.

These terms should be added as an explicitly new development model and tested
on another untouched cohort. They cannot be fitted on these 18 outcomes and
then reported as validation on the same records.

## Execution disclosure

The rank candidate itself was frozen before the HyTunnel raw archive was
accessed. The HyTunnel files had already been used for non-spatial
sensor-array means and mass-flow validation, but individual sensor positions,
individual response statistics and spatial rank metrics had not been opened or
computed when this spatial protocol was committed.

The first spatial run evaluated seven cases and exposed empty `S.pos` cells on
extra channels in the other eleven cases. A disclosed format-only repair skips
only channels with no three-coordinate position, as already allowed by the
protocol. It does not inspect concentration values when selecting channels.
The initial failure result and amendment are retained.

## Reproduction

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\run_hytunnel_spatial_holdout.py `
  --data-directory <directory-containing-the-declared-MAT-files>
```

- Dataset: <https://doi.org/10.23642/USN.14405903>
- Associated article: <https://doi.org/10.3390/en14113008>
- Frozen protocol: `research/hytunnel_spatial_holdout_protocol_2026_10_08.json`
- Format amendment: `research/hytunnel_spatial_format_amendment_2026_10_08.json`
- Final result: `research/hytunnel_spatial_holdout_result_2026_10_08.json`
- Raw MAT files committed: **no**

## Claim boundary

This result tests spatial rank transfer in one mechanically ventilated
enclosure with a vertically downward source. It does not validate
concentration amplitude, alarm or trip setpoints, outdoor station detector
placement, CFD, ESD, consequence distance or the complete station loop.
