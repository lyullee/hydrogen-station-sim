# Priority data request packet (2026-10-10)

이 문서는 공개 논문과 카탈로그에서 확인된 후보에게 보낼 **최소 요청
패킷**이다. 외부 연락은 보내지 않았고, 이 파일은 데이터가 존재한다는
증거가 아니다. 목적은 전체 원시 로그를 요구하지 않고, 독립 검증에 필요한
비식별 이벤트만 받는 것이다.

## 한 번에 요청할 최소 자료

후보 기관은 아래 조건을 만족하는 3개 이벤트만 먼저 제공하면 된다.

필수 채널:

1. 이벤트 시작 후 경과시간(공통 시계);
2. 충전기 또는 충전소 경계 압력;
3. 공급가스 또는 경계 온도;
4. 질량유량 또는 누적 전달질량;
5. 공정 단계와 시작·정지 시각;
6. 단위, 초기조건, 데이터 품질 플래그.

가능하면 다음도 포함한다.

- 수용 용기/차량 압력·온도와 용량;
- 선택된 저장뱅크와 밸브 상태;
- 프리쿨러 출구 온도;
- ESD, 중단, 고장, 교정 상태.

## 개인정보·영업기밀 보호

- 원본은 제공기관이 보관하고, 저장소에는 비식별 파일 또는 custodian-run
  결과만 남긴다.
- 회사명, 주소, 제조사, 시리얼, 정확한 달력 날짜, 원본 파일명과 원시
  행은 받지 않는다.
- 이벤트 ID는 무작위 별칭으로 바꾸고, 시간은 이벤트 시작 기준의 경과시간으로
  변환한다.
- 제공 전에 데이터 사전, 단위, 채널 역할, 공통 시계와 해시를 확인한다.
- 모델·프로토콜·분할·오차 기준을 파일을 열기 전에 동결한다. holdout에
  맞춘 계수 조정, 시간 이동, 실패 사례 제거는 하지 않는다.

## 우선 후보

| 순위 | 후보 | 기대 효과 | 현재 상태 |
|---:|---|---|---|
| 1 | RHeaDHy 2026 station-to-truck matrix, DOI [10.5281/zenodo.16992589](https://doi.org/10.5281/zenodo.16992589) | full-loop 외부 검증 | 공식 시험 매트릭스는 확인했지만 동기화 결과 파일은 공개되지 않음 |
| 2 | Wan et al. 2026 Type III/IV aspect-ratio study, DOI [10.1016/j.ijhydene.2026.156406](https://doi.org/10.1016/j.ijhydene.2026.156406) | 현재 Type-III 열 모델 실패 원인과 형상 전이 검증 | 원시 로그와 재사용 조건 요청 필요 |
| 3 | Deng et al. 2025 high-flow study, DOI [10.1016/j.ijhydene.2025.151093](https://doi.org/10.1016/j.ijhydene.2025.151093) | 대형 Type-IV 고유량 경계·열응답 검증 | 원시 로그와 채널 사전 요청 필요 |

## 영문 요청문

```text
Subject: Request for a small de-identified validation subset for hydrogen refuelling research

We are validating a hydrogen-refuelling-station digital twin and an evidence-grounded
operator decision-support layer. We do not need the complete operational archive.
Would you be able to provide three de-identified refuelling events with a common
elapsed-time axis, station/dispenser pressure, delivered-gas or boundary temperature,
mass flow or transferred mass, protocol phase, units, initial conditions and quality
flags? Vehicle/receptacle pressure and temperature, tank capacity, cascade selection,
precooler and ESD states are highly useful but optional for the first pilot.

The custodian may retain the raw files. We can accept a custodian-run evaluation or a
hash-locked de-identified export. We will freeze the model, scoring protocol and
holdout split before opening numerical outcomes, will not fit case-specific parameters,
and will publish only aggregate derived metrics. Please also state the permitted use of
derived figures and repository/journal deposition.
```

## 수락 후 처리

1. `src/h2station/privacy_safe_full_loop_intake.py`로 스키마와 개인정보를 먼저
   검사한다.
2. 파일 해시와 채널 역할을 기록하고, 모델·프로토콜·분할을 동결한다.
3. 차량/수용부 채널이 있으면 station-to-receiving-vessel 후보로 평가한다.
4. 차량 채널이 없으면 station-side 경계 진단으로만 보고한다.
5. 모든 실패와 결측을 유지하고, 통과한 경우에도 현장 안전거리나 규제 적합성으로
   확장하지 않는다.

## 현재 결정

이 패킷은 연락처를 자동으로 찾거나 메시지를 보내지 않는다. 승인된 기관 메일
채널과 수신기관을 정한 뒤 사용한다. 그 전까지 full-loop 검증 게이트와 목표
완료 상태는 닫힌다.
