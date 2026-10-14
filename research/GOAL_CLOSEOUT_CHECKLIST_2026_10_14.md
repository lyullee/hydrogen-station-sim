# 프로젝트 잔여 작업 종료 체크리스트

기준 커밋: `befd83d`
기준일: 2026-10-14

이 문서는 수소충전소 디지털 트윈·SAGA 세션 목표의 종료 조건을 한 곳에서
확인하기 위한 체크리스트다. PASS는 구현·문서·재현성 확인을 뜻하며, 독립
물리검증이 통과했다는 의미로 확장하지 않는다.

## 현재 종료 판정

| 항목 | 상태 | 근거 |
|---|---|---|
| 최신 전체 회귀 | 완료 | 1,626 passed / 0 failed / 0 skipped / 224 warnings |
| IJHE 형식·PDF 무결성 | 완료 | 24페이지 컴파일, 인용·그림·참조·PDF 해시 확인 |
| readiness 원장·미러 동기화 | 완료 | 135 PASS / 11 FAIL / 6 PENDING |
| 릴리즈 비밀값 정적 감사 | 완료 | 고신뢰 비밀값 0건·환경파일 0개·추적 파일 2,287개 검사 |
| GitHub 우선순위 CI | 완료 | 커밋 `befd83d` 실행 38582577038 성공 |
| 논문 제출 준비 | 부분 완료 | 저자·선언 메타데이터와 형식 게이트는 PASS; 독립 물리 게이트는 한계로 유지 |
| 전체 목표 완료 | 미완료 | `full_user_objective_ready=false` |

## 사용자 확인으로 닫을 항목

`manuscript/submission_metadata.json`은 제공된 JLPPI 원고와 ORCID 정보로 잠겼다. 다음 항목은 현재 메타데이터에 반영되어 readiness 게이트가 PASS다.

- 모든 저자명·소속·기관 이메일·교신저자·ORCID
- CRediT 역할과 저자 순서
- 연구비와 이해상충 문구
- AI 사용 공개·데이터 이용·윤리 문구

사람 대상 SAGA 효과성 주장은 여전히 본 논문 범위에서 제외한다.

## 새 독립 원자료가 있어야 닫을 항목

결과를 사후 재튜닝해 PASS로 바꾸지 않고, 아래 입력이 확보되면 사전 고정된
프로토콜로 재실행한다.

- Type-III 충전의 시간별 입구 경계·탱크 온도 원자료
- PRESLHY ambient·Part-B·revised holdout 원시 trace
- Proust 90 MPa와 Schefer 2006/2007의 권리 정리된 원시 trace
- Grüne 2014의 재사용 가능한 pressure-time 원자료
- 실제 수소 공간좌표·방출방향·센서별 응답이 포함된 H2SAFE/HyTunnel 독립 cohort
- 야외 누출·제트화재·피해영향을 평가할 수 있는 독립 consequence trace

## 논문에 유지할 한계

- 동기화된 station-to-vehicle 전체 루프 원자료가 없어 전체 현장 검증을 주장하지 않는다.
- SAGA가 운영자 안전의사결정을 개선한다는 효과성 주장은 전문가·윤리 평가 전에는 하지 않는다.
- HyRAM 및 피해영향 거리는 모델·표본점 기반 결과이며 법정 안전거리나 대피반경이 아니다.
- 실패·보류 물리 게이트는 개발 진단과 후속 검증계획으로만 제시한다.
- 비공개 KGS 원자료의 원시 행·시설·제조사·정확한 날짜는 공개하지 않는다.

## 재현 산출물

- [IJHE 재현 실행 기록](ijhe_reproduction_run_2026_10_14.json)
- [최신 전체 회귀 기록](full_regression_test_run_2026_10_14.json)
- [제출 준비 요약](../manuscript/submission_readiness.md)
- [잔여 작업 triage](REMAINING_WORK_TRIAGE_2026_10_14.md)
