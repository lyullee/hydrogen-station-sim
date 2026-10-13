# Figshare 실제 수소 채널 공간 검지기 holdout — 2026-10-14

USN Figshare의 `10.23642/usn.26117989.v2` 공개 자료는 개방형 직사각 채널에서 수행한 실제 수소 분산시험이다. 자료 설명상 29개 수소 검지기의 시간별 농도와 질량유량·충전압력이 제공되며, 22개 시험 archive가 현재 로컬에 존재한다. 데이터 라이선스는 CC BY 4.0이다.

## 적용 범위

이 자료는 저장소의 이전 진단에서 이미 열어 본 archive다. 따라서 아래 규칙은 결과를 재현하기 위한 고정 계약으로 유지하지만, 이번 실행은 **독립 holdout이나 전향 검증이 아닌 사후 전이 진단**으로 분류한다. 결과가 좋아도 독립 검증 게이트나 runtime 검지기 라우팅을 바꾸지 않는다.

## 동결 규칙

- 프로토콜 동결 시점에 존재한 `23_FFI_P101_T*.zip` 22개를 모두 평가 대상으로 고정한다.
- 결과를 본 뒤 케이스를 고르거나 교체하지 않는다.
- 같은 좌표계의 방출 위치·센서 좌표, 방출 방향 또는 채널 축, 공통 시간축, 센서별 수소 농도, 질량유량 또는 공급압력, 단위를 모두 확인해야 적격이다.
- 현재 `src/h2station/spatial_detector.py`의 좌표·방향·경계조건 기반 순위를 그대로 사용하며 파라미터를 맞추지 않는다.
- 실행 명령: `python scripts/run_figshare_h2_channel_spatial_holdout.py --raw-dir data/public_validation/raw/figshare_26117989`

## 판정

적격 케이스가 10건 이상이고 평균 top-5 recall과 케이스별 Spearman ρ 기준을 모두 통과해야 transfer PASS다. 입력 좌표나 단위가 없으면 모델 실패가 아니라 자료 적격성 실패로 기록한다. 수치 실패 시 후보는 runtime에 승격하지 않는다.

이 검증은 개방형 채널의 실제 수소 농도 순위에만 한정된다. 충전소 전체 검지기 지도, 경보·ESD 설정값, 피해영향거리, 대피거리, 운전자 대응을 검증하는 자료로 확대하지 않는다.

프로토콜 JSON: `research/figshare_h2_channel_spatial_holdout_protocol_2026_10_14.json`

결과 JSON: `research/figshare_h2_channel_spatial_holdout_result_2026_10_14.json`
