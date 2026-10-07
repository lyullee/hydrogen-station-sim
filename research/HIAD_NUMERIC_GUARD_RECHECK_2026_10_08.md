# HIAD direct-answer numeric guard recheck

## Result

The post-outcome runtime safety recheck completed all 34 public HIAD hydrogen-refuelling-station cases without a provider failure. Unsupported value/unit claims visible at the direct API boundary decreased from **3/34 responses (8.8%)** in the retained benchmark to **0/34 (0%)** after SAGA commit `bce9732fb112644d13b0fabb858308c09a4351b1`.

The output guard intervened in 5/34 responses. It removed the complete sentence containing a precise value/unit combination absent from the supplied question and serialized digital-twin context, then inserted an explicit verification notice. The affected HIAD event identifiers were 463, 803, 884, 1038, and 1204. Mean end-to-end in-process API latency was 604.1 ms.

| Check | Retained benchmark | Guard recheck |
|---|---:|---:|
| Public HIAD HRS cases | 34 | 34 |
| Responses exposing unsupported value/unit claims | 3 | 0 |
| Provider failures | 0 | 0 |
| Responses where the guard inserted a notice | n/a | 5 |
| Mean SAGA response latency | 696.4 ms | 604.1 ms |

## Interpretation boundary

This is a post-outcome runtime safety diagnostic on the already observed cohort. It demonstrates that the API boundary did not expose a value/unit phrase absent from the supplied input under this rerun. It does not establish that every remaining qualitative statement is correct, that the response recommends the best action, or that the system improves operator performance or field safety.

The original frozen benchmark remains unchanged. Because model outputs and the failure mode were already observed before this guard was implemented, this recheck is not an independent holdout or confirmatory effectiveness result. Independent expert scoring and a prospectively locked study remain necessary.

## Reproduction

Run from the digital-twin repository with the SAGA repository available as its sibling directory:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts\run_hiad_numeric_guard_recheck.py
```

The runner uses an in-process FastAPI `TestClient`; it does not open or retain a web server. The machine-readable result is `research/hiad_machine_response_guard_recheck_2026_10_08.json`.

