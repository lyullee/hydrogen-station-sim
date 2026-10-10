# 검증 진행 브리프 (privacy-safe)

> 이 문서는 현재 저장소에 있는 근거를 주장 범위별로 정리한 상태판입니다. 원자료 행, 태그, 경로, 사업장·제조사·정확한 날짜는 포함하지 않습니다.

## 현재 판정

- IJHE 내부 게이트: **PASS 127 / FAIL 10 / PENDING 7**.
- 제한된 투고 준비: **아직 불가**.
- 현재 주 목표: **station-side 안전 디지털 트윈·구성요소 검증·근거 기반 SAGA 응답**.
- 동기화 station-to-vehicle full-loop 검증: **주 목표에서 제외하고 논문 한계로 명시**.
- 개정 주 목표 보조 지표: **기록 없음 PASS / 기록 없음 FAIL / 기록 없음 PENDING = 기록 없음%**. 범위 조정 결과이지 새 검증 통과가 아닙니다.

## 지금 바로 사용할 수 있는 근거

- 비식별 station-side 원자료: 56,854,143개 행, 고압 압력 사이클 16,770건, 중·고압 연계 11,770건, 재충전 압력 예측 1,418건. 압력·cascade·재충전 동역학 진단에 사용합니다.
- 같은 자료의 시간순 holdout: 압력 경계 30점, cascade 3,664쌍, 재충전 예측 394건. 차량 충전 정확도나 현장 안전한계로 확대하지 않습니다.
- 공개 Type-IV 탱크 경계 검증: 12건, 탱크 경계 구성요소 검증으로 유지합니다.
- 사고 전례·대응 플레이북·가상 조치 실행은 시나리오와 단계별 대응 근거로 사용하며, 사고 빈도나 현장 대응 효과를 추정하지 않습니다.

## 실패 또는 제한된 결과도 그대로 유지

- 공개 MC Default full-loop holdout: 0 / 8 통과. 평균 압력 RMSE 15.862 MPa, 온도 RMSE 13.230 °C, SOC RMSE 18.082%p. 이 결과는 숨기거나 재평가로 대체하지 않습니다.
- NREL 탱크 경계 자료: 압력 RMSE 6.164 MPa로 현재 스크리닝을 통과하지 못해 진단용으로만 유지합니다.
- 새 full-loop 측정 코호트: **확인되지 않음**. 현재 주된 공백은 동기화된 차량·수용용기 측 채널입니다.

## 추가 자료 없이 진행 가능한 작업

1. station-side 압력·cascade·재충전 모델과 시간순 holdout을 논문용 방법·결과로 정리합니다.
2. 공개 탱크·방출·검지·사고 자료는 구성요소 진단과 LLM 근거 연결에 사용합니다.
3. full-loop가 아닌 범위로 안전 시나리오, 단계별 대응, 가상 밸브·ESD 조치의 실행 가능성을 평가합니다.
4. 결과 화면과 LLM은 위 주장 경계를 자동 표시해 station-side 결과가 차량 full-loop 검증처럼 보이지 않게 합니다.

## 선택적 후속 확장 (현재 목표의 필수 조건 아님)

- 향후 full-loop를 별도 확장할 경우에만 비식별 이벤트 **3건 이상**.
- 공통 경과시간, station/디스펜서 압력, 공급가스 또는 경계 온도, 질량유량/이송질량, 프로토콜 시작·종료 상태.
- 가능하면 차량·수용용기 압력·온도, cascade 선택 상태, precooler 출구온도, ESD·fault 전이.
- Units, initial conditions, sensor quality, synchronization and reuse rights must be confirmed by the custodian; raw files need not be published.
- The synchronized station-to-vehicle data gap is documented as a paper limitation and is no longer a required goal gate.
- 윤리·전문가 평가는 물리 모델 검증이 아니라 SAGA가 사람의 안전 판단을 개선한다고 주장할 때 필요한 별도 사람 대상 평가입니다. 그 주장을 하지 않으면 미실시 한계로 명시합니다.

## 근거 파일

- `research/data_coverage_summary_2026_10_10.json`
- `research/ijhe_readiness_audit.json`
- `research/local_candidate_full_loop_screen_2026_10_09.json`
- `research/GOAL_SCOPE_AMENDMENT_2026_10_11.md`
- `research/PUBLIC_STATION_TO_VEHICLE_SEARCH_2026_10_11.md`
- `data/public_validation/results/closed_loop_external_holdout/validation.json`

이 브리프는 모델이나 검증 게이트를 변경하지 않습니다. 새로운 자료가 들어오면 동일한 동결·시간축·권한 검사를 거친 뒤 다시 생성합니다.
