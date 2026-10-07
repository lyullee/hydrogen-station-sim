# HIAD retrospective SAGA machine benchmark

The current direct-answer SAGA path was run once on all 34 public hydrogen
refuelling station cases in the existing HIAD 2.2 inventory. The run used the
in-process FastAPI application, so no development server was opened. Historical
emergency-action, lesson and corrective-action prose was withheld from the
model. Scoring used the coarse action categories that had already been derived
for development, plus five response-stage keyword families.

| Variant | Responses | Machine proxy | Category recall | Stage coverage | Unsupported value/unit responses | Failed calls | Mean latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Alarm-only | 34 | 0.401 | 0.189 | 0.600 | 0 | 0 | 0 ms |
| SAGA-linked | 34 | 0.760 | 0.524 | 0.982 | 3 | 0 | 696 ms |

The mean paired SAGA-minus-alarm proxy difference was **0.360**. The fixed
10,000-replicate case bootstrap interval was **0.309 to 0.411**. All 34 provider
calls returned, but three responses introduced value/unit combinations absent
from the supplied historical observation. Those responses remain in the result
and are not edited or excluded.

This is a retrospective development benchmark. The action-category taxonomy
was known before collection, and the automated keyword proxy does not establish
whether advice is correct, safe or usable. It cannot support a field-safety or
SAGA-effectiveness claim. The locked independent expert study remains required.

Reproducibility artifacts:

- Protocol: `research/hiad_machine_response_benchmark_protocol_2026_10_08.json`
- Result: `research/hiad_machine_response_benchmark_2026_10_08.json`
- Runner: `scripts/run_hiad_machine_response_benchmark.py`
- Protocol SHA-256: `c3478edf3e9a5e9c7b004d10cf5f7df2f8a666c22a344d342c9bb09c138b10ad`
- Result SHA-256: `7293cd3723ef2421a05e659db73020f2a566f427aa119936ea2946fbb4c2a87c`

