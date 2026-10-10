# Validation gap triage (privacy-bounded)

현재 검증 게이트를 데이터 공백, 모델 공백, 검토 공백으로 분류한 의사결정용 보고서다. 새로운 수치 검증을 수행하거나 실패 게이트를 승격하지 않는다.

- PASS 127 / FAIL 10 / PENDING 7
- 완전한 사용자 목표 준비 여부: 아니오
- 주된 병목: synchronized receiving-vessel/controller channels and independent protocol provenance

## 미해결 게이트

| 우선순위 | 병렬 트랙 | 게이트 | 상태 | 다음 최소 행동 |
| --- | --- | --- | --- | --- |
| P0 | full_loop_intake_and_scoring | `full_loop_external_validation` | FAIL | 동기화된 충전 이벤트 최소 3건부터 비식별 intake로 접수한다. 수용부 압력·온도와 protocol_phase가 없으면 full-loop 주장을 열지 않는다. |
| P1 | component_model_repairs | `dickens_typeiii_prospective_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P1 | component_model_repairs | `grune_2014_pressure_decay_validation` | PENDING | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P1 | component_model_repairs | `h2safe_spatial_detector_transfer_validation` | FAIL | 공간좌표·방출방향·센서별 수치응답이 함께 있는 독립 holdout을 추가하고, 통과 전 runtime 자동 라우팅을 유지하지 않는다. |
| P1 | component_model_repairs | `hytunnel_carpark_dispersion_validation` | FAIL | 공간좌표·방출방향·센서별 수치응답이 함께 있는 독립 holdout을 추가하고, 통과 전 runtime 자동 라우팅을 유지하지 않는다. |
| P1 | component_model_repairs | `hytunnel_carpark_mass_flow_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P1 | component_model_repairs | `preslhy_partb_ambient_external_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P1 | component_model_repairs | `preslhy_revised_holdout_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P1 | component_model_repairs | `proust_independent_release_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P1 | component_model_repairs | `schefer_2007_pressure_decay_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P1 | component_model_repairs | `schefer_transient_release_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P2 | review_and_publication | `hiad_casebook_frozen` | PENDING | 고정된 HIAD 평가 프로토콜에 따라 casebook·응답·전문가 평가를 수집하고 freeze hash를 남긴다. |
| P2 | review_and_publication | `hiad_holdout_collection` | PENDING | 고정된 HIAD 평가 프로토콜에 따라 casebook·응답·전문가 평가를 수집하고 freeze hash를 남긴다. |
| P2 | review_and_publication | `independent_expert_review_complete` | PENDING | 고정된 HIAD 평가 프로토콜에 따라 casebook·응답·전문가 평가를 수집하고 freeze hash를 남긴다. |
| P2 | review_and_publication | `institutional_ethics_determination` | PENDING | 기관의 승인·면제·비대상 중 하나와 식별자를 확정하고 연구 기록에 보존한다. |
| P2 | review_and_publication | `saga_effectiveness_and_safety_supported` | PENDING | 고정된 HIAD 평가 프로토콜에 따라 casebook·응답·전문가 평가를 수집하고 freeze hash를 남긴다. |
| P2 | review_and_publication | `submission_metadata_and_declarations` | PENDING | 저자·기여·이해상충·자금·AI 사용 공개를 확인한 뒤 제출 메타데이터를 잠근다. |

## 실행 순서

- **P0** full-loop intake와 frozen scoring을 먼저 확인합니다. 이 트랙이 닫히면 전체 목표에 가장 큰 변화가 생깁니다.
- **P1** 실패한 구성요소 물리는 독립 holdout별로 병행합니다. 하나가 끝날 때까지 다른 트랙을 기다리지 않습니다.
- **P2** 윤리·전문가 검토·투고 메타데이터는 계산과 별도로 병행합니다.
- 전체 회귀는 코드 변경이 있는 트랙에서만 실행하고, 상태 확인에는 이 보고서와 focused test만 사용합니다.

## 사용 원칙

- FAIL 결과는 모델을 맞추기 위해 재튜닝하지 않고 그대로 보존한다.
- component 진단은 계속 사용할 수 있지만 full-loop·현장 안전거리·안전 인증으로 확장하지 않는다.
- 원시 데이터를 공개하기 어려운 경우 custodian이 원시 파일을 보관하고, 비식별 이벤트와 해시·역할 증명·집계 지표만 전달한다.
- 이 보고서는 회사·사이트·제조사·정확한 날짜·원시 경로를 포함하지 않는다.
