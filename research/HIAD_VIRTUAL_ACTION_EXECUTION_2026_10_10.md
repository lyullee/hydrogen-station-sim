# HIAD virtual response-action execution consistency

공개 사고자료에서 추출한 조치 범주를 대표 가상 시나리오의 안전명령으로 연결하고,
명령 수락·피드백·공정상태 변화까지 확인한 시뮬레이션 전용 회귀검사입니다.

- 실행 가능한 response family: **9**
- family 통과: **9/9**
- 실행 명령 수: **39**
- 피드백 고장 분리 검사: **passed**

| Family | 대표 노드 | 명령 수 | 피드백 | 상태 |
|---|---|---:|---|---|
| `compressor_thermal` | `N06` | 2 | 2/2 | `passed` |
| `external_fire` | `N08` | 7 | 7/7 | `passed` |
| `fueling_fault` | `N11` | 3 | 3/3 | `passed` |
| `gas_release` | `N08` | 6 | 6/6 | `passed` |
| `hose_connection` | `N13` | 3 | 3/3 | `passed` |
| `hydrogen_fire` | `N08` | 7 | 7/7 | `passed` |
| `isolation_failure` | `N11` | 4 | 4/4 | `passed` |
| `overpressure` | `N08` | 5 | 5/5 | `passed` |
| `precooling_fault` | `N12` | 2 | 2/2 | `passed` |

## Claim boundary

- Each sequence is a simulation-only command/feedback replay using representative node IDs; it is not a reconstruction of a historical HIAD event.
- A pass means the registered template is accepted by the virtual runtime, changes the requested process/safety state, and reports completion feedback.
- The stuck-open check confirms command and feedback are kept separate; it does not estimate field valve reliability or diagnostic sensitivity.
- No operator benefit, LLM effectiveness, accident frequency, consequence distance or field safety claim is made.
- Structural damage remains excluded because the current process model has no structural mechanics.
