# HIAD Action-to-Playbook Coverage Audit

이 문서는 공개 HIAD 조치 범주와 시뮬레이터 대응계획의 추적성만 검사합니다.
사고 조치의 옳고 그름, 물리 검증, 확률, LLM 효능은 평가하지 않습니다.

- 사고 사례: **34**
- 조치 범주: **8/8**
- 사례 연결: **34/34**
- 계약 통과: **True**

| 조치 범주 | 사례 수 | 연결 계획 수 | 단계 완비 |
|---|---:|---:|:---:|
| `detection_alarm_monitoring` | 14 | 7 | 예 |
| `emergency_communication_coordination` | 17 | 7 | 예 |
| `evacuation_perimeter_access` | 6 | 5 | 예 |
| `fire_response_cooling` | 6 | 2 | 예 |
| `inspection_leak_test_repair` | 21 | 9 | 예 |
| `procedure_interlock_training_design` | 23 | 16 | 예 |
| `shutdown_isolation_depressurization` | 22 | 12 | 예 |
| `ventilation_purge` | 21 | 5 | 예 |

This audit verifies only that public HIAD action categories have a traceable five-stage response plan in the simulator. It does not judge incident actions, validate physics, estimate probabilities, or evaluate SAGA/LLM effectiveness or safety. The records remain excluded from the blinded HIAD holdout.
