# 영향 우선 검증 게이트 매트릭스

생성 시각: 2026-10-10T19:32:53.552844+00:00
현재 게이트: 127 PASS / 10 FAIL / 7 PENDING (88.2%)

모든 게이트를 순차적으로 처리하지 않고 P0와 P1을 독립 작업으로 병렬 진행한다. P2 문서·메타데이터는 P0/P1을 막지 않는다.

## P0
- **full_loop_external_validation** (FAIL)
  - 다음 조치: 외부 기관의 동기화된 충전소·차량 계측 8건 이상을 확보하고, 모델·프로토콜을 먼저 고정한 뒤 재현성 평가
  - 담당/입력: 데이터 제공기관/검증 담당
- **hiad_casebook_frozen** (PENDING)
  - 다음 조치: 윤리 결정 후 24개 사건 케이스북 고정, 3인 독립 평가자에게 alarm/direct/RAG 응답을 수집·분석
  - 담당/입력: 연구책임자/독립 평가자
- **hiad_holdout_collection** (PENDING)
  - 다음 조치: 윤리 결정 후 24개 사건 케이스북 고정, 3인 독립 평가자에게 alarm/direct/RAG 응답을 수집·분석
  - 담당/입력: 연구책임자/독립 평가자
- **independent_expert_review_complete** (PENDING)
  - 다음 조치: 윤리 결정 후 24개 사건 케이스북 고정, 3인 독립 평가자에게 alarm/direct/RAG 응답을 수집·분석
  - 담당/입력: 연구책임자/독립 평가자
- **institutional_ethics_determination** (PENDING)
  - 다음 조치: 기관의 인간대상 연구 해당 여부 또는 면제/비해당 결정을 문서화
  - 담당/입력: 기관 IRB/연구책임자
- **saga_effectiveness_and_safety_supported** (PENDING)
  - 다음 조치: 윤리 결정 후 24개 사건 케이스북 고정, 3인 독립 평가자에게 alarm/direct/RAG 응답을 수집·분석
  - 담당/입력: 연구책임자/독립 평가자

## P1
- **dickens_typeiii_prospective_validation** (FAIL)
  - 다음 조치: 현재 실패를 유지한 채 새 공개 원자료가 들어오면 사전 동결 프로토콜로 재평가
  - 담당/입력: 모델 검증 담당
- **grune_2014_pressure_decay_validation** (PENDING)
  - 다음 조치: 현재 실패를 유지한 채 새 공개 원자료가 들어오면 사전 동결 프로토콜로 재평가
  - 담당/입력: 모델 검증 담당
- **h2safe_spatial_detector_transfer_validation** (FAIL)
  - 다음 조치: 현재 실패를 유지한 채 새 공개 원자료가 들어오면 사전 동결 프로토콜로 재평가
  - 담당/입력: 모델 검증 담당
- **hytunnel_carpark_dispersion_validation** (FAIL)
  - 다음 조치: 현재 실패를 유지한 채 새 공개 원자료가 들어오면 사전 동결 프로토콜로 재평가
  - 담당/입력: 모델 검증 담당
- **hytunnel_carpark_mass_flow_validation** (FAIL)
  - 다음 조치: 현재 실패를 유지한 채 새 공개 원자료가 들어오면 사전 동결 프로토콜로 재평가
  - 담당/입력: 모델 검증 담당
- **preslhy_partb_ambient_external_validation** (FAIL)
  - 다음 조치: 현재 실패를 유지한 채 새 공개 원자료가 들어오면 사전 동결 프로토콜로 재평가
  - 담당/입력: 모델 검증 담당
- **preslhy_revised_holdout_validation** (FAIL)
  - 다음 조치: 현재 실패를 유지한 채 새 공개 원자료가 들어오면 사전 동결 프로토콜로 재평가
  - 담당/입력: 모델 검증 담당
- **proust_independent_release_validation** (FAIL)
  - 다음 조치: 현재 실패를 유지한 채 새 공개 원자료가 들어오면 사전 동결 프로토콜로 재평가
  - 담당/입력: 모델 검증 담당
- **schefer_2007_pressure_decay_validation** (FAIL)
  - 다음 조치: 현재 실패를 유지한 채 새 공개 원자료가 들어오면 사전 동결 프로토콜로 재평가
  - 담당/입력: 모델 검증 담당
- **schefer_transient_release_validation** (FAIL)
  - 다음 조치: 현재 실패를 유지한 채 새 공개 원자료가 들어오면 사전 동결 프로토콜로 재평가
  - 담당/입력: 모델 검증 담당

## P2
- **submission_metadata_and_declarations** (PENDING)
  - 다음 조치: 현재 실패를 유지한 채 새 공개 원자료가 들어오면 사전 동결 프로토콜로 재평가
  - 담당/입력: 모델 검증 담당

## 운영 원칙

- 사후 접근 개발진단은 독립 검증 통과로 승격하지 않는다.
- 새 데이터가 도착하면 모델과 판정 규칙을 먼저 고정하고, 실패 사례를 분모에서 제외하지 않는다.
- 이 문서는 우선순위만 정하며 검증 결과 자체를 변경하지 않는다.
