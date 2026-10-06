# 비식별 저장탱크 역할별 압력 envelope

`confidential_bank_role_pressure_envelopes_2026_10_06.json`은 소유자 관리 원본 로그에서 저장탱크 역할을 확인한 뒤, 원본 행·태그·사업장·정확한 날짜·제조사 정보를 제외하고 집계한 진단용 근거다.

- 역할: `medium_storage_pressure`, `high_storage_pressure`
- 제공 정보: 표본 수, P05·중앙값·P95 압력, 양의 압력 상승률 P95, 재가동 여유 후보
- 사용처: LLM이 현재 시뮬레이션 압력의 관측 범위와 충전 재개 여유를 설명할 때 사용하는 보조 근거
- 보호 경계: 원본 행과 식별자는 저장소에 남기지 않으며 차량측 채널·온도·유량의 단위와 역할은 검증하지 않는다.

이 artifact는 운전 제어기나 안전 차단값에 자동 적용되지 않는다. 따라서 관측 envelope가 시뮬레이션과 가깝다는 사실만으로 현장 안전 한계, 피해거리, 차량 연결부 정확도, full-loop 검증 또는 보편적인 운영 한계를 주장할 수 없다. `runtime_parameter_application=false`와 `full_loop_holdout_eligible=false`는 이 경계를 기계적으로 유지하기 위한 필드다.

일부 로그에는 정지·초기화 구간의 낮은 값이 포함될 수 있으므로 LLM과 분석자는 P05·중앙값·P95를 우선 사용하고, 최소값을 안전 한계로 해석하지 않아야 한다.
