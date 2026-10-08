# SAGA grounded-measurement guard evaluation

This retained development regression covers a failure in the direct digital-twin
assistant path. Live values were present in structured JSON, but the response
guard recognized only literal value-unit pairs in prompt text. It could therefore
delete a complete sentence containing a supported consequence value.

SAGA-PY commit `54baa715227b5618861afb80eecdc20605d1842d` projects nested
`value`/`unit` pairs and unit-bearing fields such as `effect_distance_m`,
`pressure_mpa`, and `temperature_c` into explicit evidence before response
generation and guard evaluation. Equivalent numeric formatting such as `2` and
`2.0` is normalized. Main-monitor and selected-sensor endpoints are both covered.

## Retained result

The final run used clean digital-twin commit
`fbbae1bbe9376ed4851f665ff2567c1a1b8a910c`, clean SAGA-PY commit
`54baa715227b5618861afb80eecdc20605d1842d`, Groq
`qwen/qwen3.8-27b`, five repeats per case, and frozen case/rubric manifest
`2b29fcb20aeea26bc260fcb64306937859ea8dbfed0534b764da1f81ffb25a5b`.

| Case | Alarm-only score | SAGA score, mean ± SD | Range | Grounded-number coverage | Unsupported-number runs | Mean latency |
|---|---:|---:|---:|---:|---:|---:|
| Hydrogen leak | 25.0 | 88.2 ± 3.7 | 83.8–91.2 | 0.80 | 0/5 | 501 ms |
| Vehicle overheat | 40.0 | 96.7 ± 0.0 | 96.7–96.7 | 1.00 | 0/5 | 428 ms |

For the unchanged leak rubric, the pre-fix three-run diagnostic had a mean score
of 49.6, a minimum of 36.2, zero observed grounded-number coverage, and two guard
notices. The post-fix five-run diagnostic had a mean score of 88.2, a minimum of
83.8, 0.80 grounded-number coverage, and no guard notices. The mean-score change
was +38.7 points and the minimum-score change was +47.5 points.

The fueling row in the same run passed its public schedule-boundary audit. It
stopped at the pressure target with 87.8% calculated SOC, so this result must not
be represented as SAE J2601 certification or proof of full-fill thermodynamic
accuracy.

## Reproduction

Start SAGA-PY from the retained SAGA commit and run:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts\run_paper_evaluation.py `
  --saga-url http://127.0.0.1:18090 `
  --provider groq `
  --repeats 5 `
  --duration-s 360 `
  --saga-repo ..\saga-system `
  --require-saga
```

The machine-readable artifact retains source commits, the complete case and
rubric manifest, answer text, per-run scores, latency, unsupported-number checks,
and the before/after leak diagnostic:
[`saga_grounded_measurement_guard_evaluation_2026_10_08.json`](saga_grounded_measurement_guard_evaluation_2026_10_08.json).

## Claim boundary

This is a post-access software regression with unequal repeat counts (three
before and five after). It establishes that the defect was corrected under the
retained cases. It is not an independent SAGA effectiveness study, operator
benefit study, field-safety result, or regulatory compliance result. Expert and
human-factors evaluation remain required.
