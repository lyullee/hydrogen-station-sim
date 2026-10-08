# SAGA direct measurement guard regression

## Result

The deterministic regression passed **5/5** cases against SAGA commit
`af232d3`. No provider call was made.

- Equivalent temperature spellings (`-33oC` and `-33 °C`) remain visible.
- Equivalent time spellings (`10 min` and `10 minutes`) remain visible.
- A shared-unit range (`5-10 MPa`) can be restated as two explicit endpoints.
- Value/unit pairs projected from structured digital-twin fields remain visible.
- An absent value (`12 bar`) is removed and replaced by the verification notice.

This corrects an over-filtering mode in the first lexical guard. The original
34-case HIAD benchmark and post-outcome rerun remain retained unchanged; their
lexical counts are not re-labelled as expert-judged hallucination rates.

## Boundary

This is a software regression for value/unit normalization and output filtering.
It does not establish factual completeness, action correctness, operator benefit,
field safety, or SAGA effectiveness. Those claims still require the frozen
independent expert study.

## Reproduction

From the digital-twin repository with `saga-system` as its sibling directory:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts\audit_saga_measurement_guard_regression.py
```

The machine-readable result is
`research/saga_measurement_guard_regression_2026_10_08.json`.
