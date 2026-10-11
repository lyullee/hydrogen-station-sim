# Validation gap triage (privacy-bounded)

현재 검증 게이트를 데이터 공백, 모델 공백, 검토 공백으로 분류한 의사결정용 보고서다. 새로운 수치 검증을 수행하거나 실패 게이트를 승격하지 않는다.

- PASS 129 / FAIL 10 / PENDING 7
- 주 목표 범위: PASS 129 / FAIL 9 / PENDING 2 (92.1%)
- 완전한 사용자 목표 준비 여부: 아니오
- 주된 병목: independent component-physics holdouts and protocol provenance

## 미해결 게이트

| 우선순위 | 병렬 트랙 | 게이트 | 상태 | 다음 최소 행동 |
| --- | --- | --- | --- | --- |
| P0 | component_model_repairs | `dickens_typeiii_prospective_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P0 | component_model_repairs | `grune_2014_pressure_decay_validation` | PENDING | 공식 KIT·출판사 재확인에서도 원시 pressure-time 표가 없어 보류 중이다. custodian 원자료와 재사용 조건을 받은 뒤 새 pre-access protocol을 동결한다. 별도 KIT LH2 원자료는 공식 권리는 확인했지만 전체 아카이브 MD5가 검증되지 않아 이 게이트를 닫지 않는다. |
| P0 | component_model_repairs | `h2safe_spatial_detector_transfer_validation` | FAIL | 공간좌표·방출방향·센서별 수치응답이 함께 있는 독립 holdout을 추가하고, 통과 전 runtime 자동 라우팅을 유지하지 않는다. |
| P0 | component_model_repairs | `hytunnel_carpark_dispersion_validation` | FAIL | 공간좌표·방출방향·센서별 수치응답이 함께 있는 독립 holdout을 추가하고, 통과 전 runtime 자동 라우팅을 유지하지 않는다. |
| P0 | component_model_repairs | `hytunnel_carpark_mass_flow_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P0 | component_model_repairs | `preslhy_partb_ambient_external_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P0 | component_model_repairs | `preslhy_revised_holdout_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P0 | component_model_repairs | `proust_independent_release_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P0 | component_model_repairs | `schefer_2007_pressure_decay_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P0 | component_model_repairs | `schefer_transient_release_validation` | FAIL | 결과를 재튜닝하지 말고 실패한 물리량·직경·경계조건에 맞는 새 pre-access protocol과 독립 원시 trace를 확보한다. |
| P1 | review_and_publication | `hiad_casebook_frozen` | PENDING | 선택 항목: 사람 대상 SAGA 효과를 주장할 때만 고정된 HIAD 평가 프로토콜에 따라 casebook·응답·전문가 평가를 수집하고 freeze hash를 남긴다. |
| P1 | review_and_publication | `hiad_holdout_collection` | PENDING | 선택 항목: 사람 대상 SAGA 효과를 주장할 때만 고정된 HIAD 평가 프로토콜에 따라 casebook·응답·전문가 평가를 수집하고 freeze hash를 남긴다. |
| P1 | review_and_publication | `independent_expert_review_complete` | PENDING | 선택 항목: 사람 대상 SAGA 효과를 주장할 때만 고정된 HIAD 평가 프로토콜에 따라 casebook·응답·전문가 평가를 수집하고 freeze hash를 남긴다. |
| P1 | review_and_publication | `institutional_ethics_determination` | PENDING | 선택 항목: SAGA가 운영자의 안전 판단을 개선한다고 주장할 때만 기관의 승인·면제·비대상 중 하나와 식별자를 확정하고 연구 기록에 보존한다. |
| P1 | review_and_publication | `saga_effectiveness_and_safety_supported` | PENDING | 선택 항목: 사람 대상 SAGA 효과를 주장할 때만 고정된 HIAD 평가 프로토콜에 따라 casebook·응답·전문가 평가를 수집하고 freeze hash를 남긴다. |
| P1 | review_and_publication | `submission_metadata_and_declarations` | PENDING | 저자·기여·이해상충·자금·AI 사용 공개를 확인한 뒤 제출 메타데이터를 잠근다. |

## 실행 순서

- **P0** 현재 주 목표에 포함된 구성요소 물리 실패를 독립 holdout별로 병행합니다. 하나가 끝날 때까지 다른 트랙을 기다리지 않습니다.
- **P1** 투고 메타데이터는 계산과 별도로 검토하고, 윤리·전문가 평가는 사람 대상 SAGA 효과 주장을 선택할 때만 시작합니다.
- station-to-vehicle full-loop FAIL은 아래 범위 제외 목록에 보존하며, 현재 논문의 필수 작업 큐로 반복하지 않습니다.
- 전체 회귀는 코드 변경이 있는 트랙에서만 실행하고, 상태 확인에는 이 보고서와 focused test만 사용합니다.

## 사용 원칙

- FAIL 결과는 모델을 맞추기 위해 재튜닝하지 않고 그대로 보존한다.
- component 진단은 계속 사용할 수 있지만 full-loop·현장 안전거리·안전 인증으로 확장하지 않는다.
- 원시 데이터를 공개하기 어려운 경우 custodian이 원시 파일을 보관하고, 비식별 이벤트와 해시·역할 증명·집계 지표만 전달한다.
- 이 보고서는 회사·사이트·제조사·정확한 날짜·원시 경로를 포함하지 않는다.

## 주 목표에서 제외한 게이트

| 게이트 | 감사 상태 | 처리 |
| --- | --- | --- |
| `full_loop_external_validation` | FAIL | No reusable synchronized station-to-vehicle raw bundle was identified; the current paper scope is station-side and component validation. 논문 한계: Do not claim independent station-to-vehicle full-loop accuracy, vehicle-controller validation or field-safety validation. |
