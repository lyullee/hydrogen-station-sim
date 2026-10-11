# 공개 저장소 정적 비밀정보 점검

점검 시각: 2026-10-11 (UTC 기록은 `secret_scan_2026_10_11.json` 참조)

`git ls-files`로 추적된 텍스트 파일 1,837개 중 1,728개를 값 비공개 방식으로 검사했다. 작업트리 전체의 추적·비추적 `.env*` 파일도 별도로 확인했으며 발견된 파일은 0개였다. OpenAI·Groq·xAI·Google·GitHub 토큰 형식과 PEM 개인키 헤더의 고신뢰 패턴은 0건이었다. dotenv 환경변수 대입도 0건이다.

디지털 트윈은 SAGA 주소와 HyRAM 선택값을 `H2STATION_SAGA_URL`, `H2STATION_SAGA_DIRECT_URL`, `H2STATION_SAGA_CHAT_TIMEOUT_S`, `H2STATION_HYRAM_EVALUATOR` 같은 실행 환경변수에서 읽는다. 소스에 키 값을 기본값으로 넣지 않는 경계를 유지한다.

이 결과는 현재 추적 작업트리의 정적 점검이다. 실행 중인 호스트 환경변수, 무시된 파일, Git 전체 이력, 외부 SAGA 저장소의 비밀값은 포함하지 않으므로 공개 전 운영 환경과 GitHub secret scanning도 별도로 확인해야 한다. 보고서에는 실제 값이나 후보 문자열을 기록하지 않았다.
