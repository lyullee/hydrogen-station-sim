# Privacy-bounded data coverage summary (2026-10-10)

이 문서는 확보된 공개·비식별 자료로 지금 검증할 수 있는 범위와, 완전한 충전소-차량 검증에 필요한 최소 입력을 자동으로 정리한 산출물이다.

- IJHE 게이트: PASS 127 / FAIL 10 / PENDING 7
- 데이터 양이 주된 병목인가: 아니오
- 현재 주된 공백: synchronized and attested receiving-vessel/vehicle channels

## 현재 사용 가능한 검증 범위

| 영역 | 상태 | 현재 가능한 주장 | 금지된 주장 |
| --- | --- | --- | --- |
| `owner_station_side_dynamics` | ACTIONABLE | station-side pressure, cascade and recharge dynamics diagnostics | vehicle-side full-loop accuracy or field safety limits |
| `owner_station_runtime_replay` | ACTIONABLE | sanitized station pressure-boundary profile is wired and replayable | automatic runtime parameter replacement or full-loop validation |
| `public_type_iv_tank` | VALIDATED_COMPONENT | measured-boundary Type-IV tank component validation | station controller, compressor, cascade, dispenser or field safety certification |
| `public_station_tank_boundary` | DIAGNOSTIC_ONLY | 공통시계 호스·수용탱크 압력·온도·질량의 부분 station-to-tank 경계 진단 | 충전소 제어기·캐스케이드·ESD·노즐/리셉터클을 포함한 full-loop 검증 |
| `owner_station_side_integrated_validation` | VALIDATED_STATION_SIDE | hash-linked same-site station-side pressure-boundary, cascade-sequence and recharge-pressure holdout integration | vehicle-side accuracy, full station-to-vehicle validation, safety-distance or field certification; the retained lifecycle-counter result is negative |
| `nbsdc_liquid_hrs_catalogue` | REQUEST_CANDIDATE | real liquid-hydrogen refueling-station operating-range and data-access lead for station-side schema/context and LLM claim-boundary grounding | numerical model calibration, independent holdout scoring, full station-to-vehicle validation, safety-distance calculation, or response-effectiveness claim before custodian approval and channel attestation |
| `public_component_measurements` | DIAGNOSTIC_ONLY | public synchronized component pressure/temperature/flow diagnostics | prospective station-to-vehicle holdout |
| `public_type_i_filling_thermal` | DIAGNOSTIC_ONLY | 공개 Type-I 탱크 충전 열거동의 구성품 진단 및 열 모델 비교 | 충전소 제어기·캐스케이드·디스펜서·차량을 포함한 full-loop 검증 또는 런타임 파라미터 승격 |
| `public_field_metrology` | DIAGNOSTIC_ONLY | 35 MPa 현장 계측의 압력·온도·질량 경계 및 반복성 맥락 | 원시 station-to-vehicle holdout, 제어기·ESD·사고영향 검증 |
| `public_actual_h2_spatial_dispersion` | DIAGNOSTIC_ONLY | 실제 수소 저압 누출·다중 검지기 응답 범위와 사고 모델 진단 | 충전소 full-loop, 좌표기반 검지기 holdout, site-specific safety distance |
| `public_hytf_tank_boundary` | DIAGNOSTIC_ONLY | 공개 70 MPa 탱크 압력·열 응답의 구성품 경계 진단 | 질량유량, 차량 수용부, 충전소 제어기·ESD를 포함한 full-loop 검증 |
| `public_h2safe_indoor_surrogate` | DIAGNOSTIC_ONLY | 헬륨 대체가스의 실내 센서 응답·좌표 진단 | 수소 농도 환산, 충전소 외부 확산, ESD 효과 또는 안전거리 검증 |
| `public_accident_precedents` | ROUTED_FOR_GROUNDING | traceable scenario and response-plan grounding | historical frequency or response-effectiveness estimation |

## 다음 최소 입력

전체 히스토리언 대신, 공통 시간축을 가진 충전 이벤트 3건부터 요청한다.

필수 채널: common elapsed time, station or dispenser pressure, delivered-gas or boundary temperature, mass flow or transferred mass, protocol start/stop phase.

선택 채널: vehicle/receptacle pressure and temperature, selected cascade-bank state, precooler outlet temperature, ESD and fault transitions.

평가 원칙: freeze protocol and model before scoring; never fit on the holdout

## 판정

현재 자료로 설비·저장뱅크·탱크·검지기·사고 대응 근거는 계속 보강할 수 있다. 데이터 양이 주된 병목은 아니며, 완전한 IJHE 수준의 충전소-차량 외부 검증에 필요한 것은 차량 측 채널의 동기화·의미·재사용 권한이다.

공개 카탈로그에서 실제 액체수소 충전소 운전 데이터 후보를 확인했지만, 수치 파일은 데이터 신청 승인 전까지 잠겨 있다. 따라서 현재는 운전범위·파일 역할·접근 경계만 LLM 근거로 사용하고, 원자료를 받기 전에는 수치 보정이나 성능 주장을 하지 않는다.

원시 데이터를 공개하기 어렵다면 custodian이 원시 파일을 보관한 채, 비식별 이벤트 3건의 해시·역할 증명·집계 지표만 전달하는 방식으로 검증을 진행한다.

원시 행, 경로, 회사·사이트·제조사 식별자는 이 요약에 포함하지 않는다.
