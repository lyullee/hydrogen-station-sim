# HIAD accident-response coverage evaluation

공개 HIAD 원자료의 조치 문장을 재배포하지 않고, 통제된 조치 범주를 시스템의 단계별 대응계획으로 라우팅할 수 있는지 검사한 결과입니다.
이 결과는 조치의 정확성·안전성·효과성이나 LLM의 성능을 검증하지 않습니다.

- 상태: **PASS**
- 전체 사례: **34**
- 공개 조치 범주가 기록된 사례: **33**
- 범주가 기록되지 않은 사례: **1** (대응 없음으로 해석하지 않음)
- 범주 커버리지: **8/8**
- 미커버 사례-범주 쌍: **0**
- 실행명령 필수 범주: **5**
- 실행명령 미커버 사례-범주 쌍: **0**

## 범주별 단계 계약

| 공개 조치 범주 | 사례 수 | 커버 사례 | 실행 계약 | 실행 미커버 | 필수 단계 |
|---|---:|---:|---|---:|---|
| `detection_alarm_monitoring` | 14 | 14 | `staged_workflow_only` | 해당 없음 | recognition, stabilize, prevention |
| `emergency_communication_coordination` | 17 | 17 | `virtual_command_required` | 0 | immediate, prevention |
| `evacuation_perimeter_access` | 6 | 6 | `virtual_command_required` | 0 | immediate, stabilize |
| `fire_response_cooling` | 6 | 6 | `virtual_command_required` | 0 | immediate, stabilize, prevention |
| `inspection_leak_test_repair` | 21 | 21 | `staged_workflow_only` | 해당 없음 | restart, prevention |
| `procedure_interlock_training_design` | 23 | 23 | `staged_workflow_only` | 해당 없음 | prevention |
| `shutdown_isolation_depressurization` | 22 | 22 | `virtual_command_required` | 0 | immediate, stabilize, restart |
| `ventilation_purge` | 21 | 21 | `virtual_command_required` | 0 | immediate, stabilize, prevention |

## 해석 경계

This artifact shows only that action categories derived from public HIAD metadata can be routed to registered staged response plans and that active response categories expose at least one simulation-only command. Virtual responder notification never contacts an external service. A case with no recorded public category is not treated as having no response. The result does not judge source actions, validate physics, estimate risk, or demonstrate SAGA/LLM/operator effectiveness or safety. Independent expert review and blinded holdout testing remain required.

입력 해시:

- `action_evidence_sha256`: `72f2550eabea6a4207a5d59c98bd99520e217fd2d4f8597e5d1d72f2ef87e1dd`
- `response_stage_contract_sha256`: `52146ec0bf65f2be73d714f2b3f154d7bb51813b22c6bb7555549362a4b1701f`
- `action_playbook_coverage_sha256`: `8194c02019425bd217aa7bd474d82608c980ee5b1b55fcc0c86e6293210e8edf`
- `playbook_catalog_sha256`: `997da81d9f273031dc5d160d1fdee826cc1defaa3cbf5651f9bd0c7c7988e052`
- `virtual_safety_runtime_sha256`: `5d55b14ab716417ec0eb92086e0bd5c9e6a7db7f48da6baa866834db4915f775`
