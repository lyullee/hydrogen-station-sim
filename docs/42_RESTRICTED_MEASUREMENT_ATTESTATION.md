# 제한자료 측정 채널 확인

실측 원자료의 열 이름·설비명·위치·절대 시각을 공개하지 않고도, 어떤
측정 채널을 디지털 트윈 보정에 사용할 수 있는지 데이터 관리자가 확인하는
절차입니다. 이 확인은 수치 보정이나 검증 결과가 아닙니다.

## 필요한 최소 확인

제한 환경의 매핑 파일에는 원시 열 이름이 남아 있어도 됩니다. 별도 확인
파일에는 다음의 일반화한 역할만 기록합니다.

- 시간축이 실제 시간 순서를 보존하는지
- 저장·공급 압력의 단위와 물리적 역할
- 온도와 유량의 단위·방향·교정 상태
- 압축기/밸브 상태값의 의미
- 해당 계측기의 교정·품질 메타데이터 존재 여부

예시는
[`restricted_station_channel_attestation.example.json`](../research/restricted_station_channel_attestation.example.json)에
있습니다. 원시 태그명·파일 경로·설비 제조사·위치·절대 시각은 예시와
생성 결과에 넣지 않습니다.

## 실행

먼저 제한 매핑만 읽는 검토 초안을 생성합니다. 이 단계는 측정 행을 읽지
않으며, 제안 단위는 변환계수에서 표시할 뿐 확인된 값으로 취급하지 않습니다.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe scripts\build_restricted_attestation_review.py `
  --mapping <restricted-raw-column-map.json> `
  --profile-id station-equipment-generic-v1 `
  --private-draft <outside-repository-attestation-draft.json> `
  --private-markdown <outside-repository-review-checklist.md> `
  --public-status research/confidential_station_attestation_request_status.json
```

생성 초안은 `UNCONFIRMED` 상태라서 로더가 거부합니다. 관리자가 일반화한
역할·단위·압력 기준·상태값 의미를 확인하고 `review_status`를
`CUSTODIAN_CONFIRMED`로 바꾼 뒤에만 아래 검증 단계로 진행할 수 있습니다.

제한된 원자료가 있는 환경에서만 다음을 실행합니다.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe scripts\attest_restricted_station_mapping.py `
  --mapping <restricted-raw-column-map.json> `
  --attestation <restricted-generic-role-attestation.json> `
  --output <reviewable-sanitized-attestation.json>
```

명령은 측정 행을 읽지 않습니다. 출력에는 일반화한 채널 계열과 사용 가능
여부만 포함됩니다. 압력 확인이 없으면 경계 압력 보정을 허용하지 않고,
온도·유량·상태 확인이 없으면 해당 값은 진단 전용으로 남습니다.

## 현재 자료에 적용되는 범위

현재 공개된 비식별 집계는 압력 역할·단위와 압축기 상태만 확인되어 있어,
재충전 히스테리시스와 최소 재기동 대기시간에만 선택 적용됩니다. 온도와
유량은 확인 파일이 추가되기 전까지 압축기 용량·프리쿨러 성능·차량 충전
종료 예측에 사용하지 않습니다.

이 절차를 통과해도 차량 탱크·노즐·프로토콜 채널이 없으면 전체
충전소-차량 루프 검증이나 안전거리·안전인증 주장은 허용되지 않습니다.
