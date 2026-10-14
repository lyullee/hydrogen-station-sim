# 수소충전소 안전 디지털 트윈·SAGA 증거 요약

기준일: **2026-10-14**

이 문서는 현재 시스템의 정확도를 하나의 홍보용 숫자로 합산하지 않고, 공개 실험·실제 사고 자료·비식별 충전소 자료·소프트웨어 회귀를 각각의 검증 범위로 분리해 기록한다. 수치는 해당 원장과 결과 파일의 재현 가능한 결과를 그대로 옮겼으며, 통과하지 않은 물리량은 통과한 것처럼 표현하지 않는다.

## 현재 판정

| 항목 | 현재 결과 | 해석 |
|---|---:|---|
| 전체 readiness 게이트 | **134 PASS / 11 FAIL / 7 PENDING (88.2%)** | 모든 공개·비공개·선택 게이트를 포함한 보수적 원장 |
| 선언한 주 논문 범위 | **133 PASS / 10 FAIL / 2 PENDING (91.7%)** | station-to-vehicle 전체 루프와 사람 대상 효과평가를 제외한 범위 |
| 전체 Python 회귀 | **1,625 passed / 0 failed / 0 skipped / 224 warnings** | 구현·계약·근거 경계 회귀 |
| bounded IJHE 제출 준비 | **미완료** | 독립 물리 검증 실패/보류와 저자 메타데이터 미확정 |

## 공개 실험 기반 수치 검증

### Type-IV 차량 용기 모델

Powertech Labs SAE J2601 공개 자료를 사전 분할해 12개 validation case로 평가했다. 결과는 압력 RMSE **3.84 MPa**, 온도 RMSE **4.83 °C**, SOC RMSE **3.85 percentage points**다. 이 수치는 공정·차량 용기 경계가 제공된 범위의 구성요소 검증이며, 충전소 전체 제어기나 현장 안전거리 정확도를 뜻하지 않는다.

근거: [`tank_model_validation_v2.json`](tank_model_validation_v2.json)

### 실제 수소 점화 압력 피크

USN의 실제 수소 점화 압력 자료 27개 eligible case에서 27개가 고정된 구성요소 화면을 통과했다. 평균 peak overpressure 절대오차는 **0.672 kPa**, median trace NRMSE는 **19.43%**다. 이 결과는 환기된 밀폐공간의 점화 압력 피크에 한정된다.

근거: [`usn_17934047_ignited_pressure_peaking_result_2026_10_08.json`](usn_17934047_ignited_pressure_peaking_result_2026_10_08.json)

### HyRAM 영향거리 표시 계층

독립 자료군 3개와 HyRAM upstream 검증 **47 tests / 803 subtests**를 연결해 방향성 자유제트·열복사·비구속 과압 표시를 점검했다. 이 결과는 표시 매핑의 구성요소 검증이며, 특정 충전소의 법정 안전거리나 대피반경 인증이 아니다.

근거: [`consequence_geometry_validation.json`](consequence_geometry_validation.json)

## 실제 충전소 운전자료 기반 검증

공개하지 않는 소유자 통제 자료는 원시 행·시설명·제조사·절대 날짜를 저장소에 보존하지 않고, 해시 연결된 집계와 holdout 결과만 사용한다.

| 검증 영역 | holdout 규모 | 결과 |
|---|---:|---|
| 압력 경계 재현 | 30 points / 1,755 s | 지원됨 |
| 중압–고압 cascade 순서 | 3,664 pairs | 지원됨, 순차 비율 94.38% |
| 재충전 압력 예측 | 394 cases | MAE **0.184 MPa**, P90 절대오차 **0.529 MPa** |
| lifecycle counter 정렬 | 동일 holdout | 음성 결과 유지: recall 19.60%, pressure precision 90.27% |

따라서 시스템은 충전소 측 압력 경계·cascade 순서·단기 재충전 압력 보조에는 근거가 있지만, 차량 계측이 없는 상태에서 station-to-vehicle 전체 루프를 검증했다고 주장하지 않는다.

근거: [`confidential_station_side_integrated_validation_2026_10_09.json`](confidential_station_side_integrated_validation_2026_10_09.json)

## 실제 사고자료와 SAGA 근거성

- 공개 HIAD 2.2의 HRS 34건에서 8개 조치 범주가 모두 단계별 대응계획으로 연결됐다. 조치 범주가 있는 33건은 33건 모두 매핑됐고, 실행 가능한 사례-범주 연결은 72건이다.
- 비식별 실제 사고 메타데이터 322건은 모두 후보 대응계획의 5단계 계약에 연결됐고, 318건은 복수 사고군으로 분류됐다.
- 이 결과는 사고자료의 시나리오·대응 분류와 단계별 안내의 추적성을 입증한다. 실제 사고에서 어떤 조치가 효과적이었는지, SAGA가 사람의 판단을 개선했는지는 아직 평가하지 않았다.

근거: [`hiad_accident_response_coverage_evaluation_2026_10_05.json`](hiad_accident_response_coverage_evaluation_2026_10_05.json), [`confidential_local_accident_response_coverage_2026_10_06.json`](confidential_local_accident_response_coverage_2026_10_06.json)

## 현재 닫히지 않은 검증

다음 결과는 실패 또는 보류 상태이며, 사후 파라미터 조정으로 PASS로 바꾸지 않는다.

- Type-III 열전달, PRESLHY 방출, Proust/Schefer 감압·방출, Grüne 원시 압력 trace
- H2SAFE 공간 검지기 전이와 H2FillS HDVS 차량 용기 경계
- station-to-vehicle 동기 전체 루프
- SAGA의 사람 대상 효과·안전성 평가
- 논문 저자·소속·CRediT·이해상충·연구비 메타데이터 확정

이 한계 때문에 시스템의 현재 주장은 **공개 실험과 실제 사고자료로 범위가 제한된 구성요소·충전소 측 기능을 검증한 안전 디지털 트윈 및 근거 기반 의사결정 지원**으로 제한한다. 현장 배치 전에는 시설별 HAZOP, 전문가 검토, 계측 교정과 법정 안전거리 검토가 별도로 필요하다.

## 재현 기준

- 전체 회귀 기록: [`full_regression_test_run_2026_10_14.json`](full_regression_test_run_2026_10_14.json)
- 잔여 게이트: [`REMAINING_WORK_TRIAGE_2026_10_14.md`](REMAINING_WORK_TRIAGE_2026_10_14.md)
- 과업별 진행률: [`WORKSTREAM_PROGRESS_2026_10_14.md`](WORKSTREAM_PROGRESS_2026_10_14.md)
- 원장: [`goal_progress_snapshot_2026_10_14.json`](goal_progress_snapshot_2026_10_14.json)
