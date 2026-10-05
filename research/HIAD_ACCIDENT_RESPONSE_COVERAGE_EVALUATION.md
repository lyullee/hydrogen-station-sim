# HIAD accident-response coverage evaluation

공개 HIAD 원자료의 조치 문장을 재배포하지 않고, 통제된 조치 범주를 시스템의 단계별 대응계획으로 라우팅할 수 있는지 검사한 결과입니다.
이 결과는 조치의 정확성·안전성·효과성이나 LLM의 성능을 검증하지 않습니다.

- 상태: **PASS**
- 전체 사례: **34**
- 공개 조치 범주가 기록된 사례: **33**
- 범주가 기록되지 않은 사례: **1** (대응 없음으로 해석하지 않음)
- 범주 커버리지: **8/8**
- 미커버 사례-범주 쌍: **0**

## 범주별 단계 계약

| 공개 조치 범주 | 사례 수 | 커버 사례 | 필수 단계 |
|---|---:|---:|---|
| `detection_alarm_monitoring` | 14 | 14 | recognition, stabilize, prevention |
| `emergency_communication_coordination` | 17 | 17 | immediate, prevention |
| `evacuation_perimeter_access` | 6 | 6 | immediate, stabilize |
| `fire_response_cooling` | 6 | 6 | immediate, stabilize, prevention |
| `inspection_leak_test_repair` | 21 | 21 | restart, prevention |
| `procedure_interlock_training_design` | 23 | 23 | prevention |
| `shutdown_isolation_depressurization` | 22 | 22 | immediate, stabilize, restart |
| `ventilation_purge` | 21 | 21 | immediate, stabilize, prevention |

## 해석 경계

This artifact shows only that action categories derived from public HIAD metadata can be routed to registered staged response plans. A case with no recorded public category is not treated as having no response. The result does not judge source actions, validate physics, estimate risk, or demonstrate SAGA/LLM/operator effectiveness or safety. Independent expert review and blinded holdout testing remain required.

입력 해시:

- `action_evidence_sha256`: `72f2550eabea6a4207a5d59c98bd99520e217fd2d4f8597e5d1d72f2ef87e1dd`
- `response_stage_contract_sha256`: `3b4b0de8bb20af9aede25adecc22f0d0e3fb8a69c94bf2fdfd2940f265f9bee7`
- `action_playbook_coverage_sha256`: `8638b221edff2fd1c91250e8c237394b5da67823ab2745bf62da105e72f80b14`
- `playbook_catalog_sha256`: `b7d64103d9c4d3a322edd2c97b3800b5a796385e4ec25a588a252d288aad8bba`
