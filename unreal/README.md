# 수소충전소 Unreal 전환 작업

기존 Python 계산 서버의 상태를 UE5에서 표시한다. 공정·HyRAM·HAZOP·LLM 계산은 기존 서버에 남는다. 현재 전체 참조 충전소 장면, 저장 뱅크 3개, 표시 API, 웹 전환, Pixel Streaming 서버의 소스가 준비되어 있다. UE 엔진 컴파일·화면·WebRTC 영상은 엔진 설치 후 검증해야 한다.

## 현재 설치 상태

2026-10-15: Epic Games Launcher 설치 완료. VS 2022 C++ Build Tools 설치 완료, 설치 프로그램이 재부팅 필요를 보고했다. UE 엔진은 아직 설치되지 않았다. Launcher 설치 화면에서 버전 타일이 나타나지 않는 문제를 확인했으며, 자체 업데이트 파일 검증 실패 BV02/BV05와 접근 오류 기록이 있었다. 로그인 자체는 성공 기록이 있다. 잠긴 Windows 화면을 우회해 조작하지 않는다.

Launcher 자체 복구 뒤 종료·재시작을 시도했으며 Windows 잠금으로 UI 재확인은 보류됐다. Epic의 캐시 초기화 절차를 삭제 대신 날짜별 백업으로 수행하는 `scripts/repair_epic_cache.ps1`를 준비했다. 계정·설치 게임 폴더는 변경하지 않는다. 로그의 파일 검증 실패가 설치 타일 미표시의 확정 원인이라는 뜻은 아니며, 잠금 해제 후 결과 확인이 필요하다. 참고: https://www.epicgames.com/help/c-32735058/a20673770?lang=en-US

환경 확인: 저장소 루트에서 `.venv\Scripts\python.exe scripts/check_unreal_environment.py` 실행. 별도 엔진 경로는 `HRS_UNREAL_ROOT`로 지정한다. 계정·비밀번호·API 키를 이 프로젝트에 넣지 않는다.

## 서버와 프로젝트 실행

1. UE 5.6 계열 설치를 완료한다. 빌드 도구 재부팅은 다른 작업을 종료할 수 있는 시점에 사용자가 수행한다.
2. 계산 서버: `.venv\Scripts\python.exe -m uvicorn h2station.api:app --app-dir src --host 127.0.0.1 --port 8000`.
3. 엔진 경로를 지정하고 시제품 준비: `./scripts/start_unreal_pilot.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.6' -Build -Bootstrap`. 고해상도 참조 GLB까지 가져오려면 먼저 웹 자산 내보내기·Khronos 검증을 실행한 뒤 `-ImportAssets`를 추가한다. 가져오기는 기존 편집 자산을 덮어쓰지 않는다.
4. Pixel Streaming 서버: `./scripts/start_pixel_streaming.ps1`. 파일 `infrastructure-lock.json`의 버전과 커밋을 사용한다. 이 실행 스크립트는 로컬 PC에만 수신 포트를 연다.
5. UE 실행: `./scripts/start_unreal_pilot.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.6' -Run -SignallingUrl 'ws://127.0.0.1:18888'`.
6. 계산 서버 시작 전에 환경변수 `H2STATION_UNREAL_PLAYER_URL=http://127.0.0.1:18080`를 설정한다. 키가 아닌 플레이어 주소다.
7. 기존 웹에서 새 시뮬레이션을 시작하고 `Unreal 3D`를 누른다. 플레이어의 영상 시작 안내에 따라 연결한다. 표준 3D 전환은 계산을 중지하지 않는다.

UE 프로젝트 파일: `HRSUnreal/HRSUnreal.uproject`. 에셋 생성 스크립트는 이미 편집한 맵·재질을 덮어쓰지 않는다. 생성된 Content 및 바이너리는 Git에서 제외하고 소스·설정·생성 스크립트를 보관한다. 신규 UE 버전에 대한 검증은 별도로 수행한다.

## Pixel Streaming 서버 재현

공식 저장소를 `unreal/PixelStreamingInfrastructure`에 복제하고 lock 파일의 커밋으로 체크아웃한다. Node 공식 배포의 22.14.0 Windows x64 ZIP과 SHASUMS256.txt로 해시를 확인하여 `unreal/.tooling`에 풀어 둔다. 런타임과 서드파티 체크아웃은 Git에 올리지 않는다.

공식 저장소 루트에서 portable Node 폴더를 해당 셸 PATH에 추가하고 `npm ci --ignore-scripts --no-audit --no-fund`, `npm run build:all:cjs` 순서로 실행한다. Common, Signalling, 서버, 프런트엔드를 차례로 빌드한다. 설치 스크립트 실행 없이 필요한 TypeScript/webpack 빌드를 직접 실행한다. 업스트림 라이선스는 그대로 유지한다.

## 시제품 조작

왼쪽 버튼 드래그는 회전, 중간 버튼 드래그는 이동, 휠은 확대·축소다. 클릭 또는 1/2/3 키로 저/중/고압 뱅크를 선택한다. X는 선택 뱅크 입구 차단, Z는 출구 차단, E는 가상 ESD, F는 모든 공정 정지, R은 위험도 바닥, D는 표본 영향거리다. C는 CCTV 위치, G는 가스·화염 검지기 위치를 켜고 끈다. 기본값은 두 위치 표시 모두 꺼짐이다. 키 조작은 시뮬레이션 서버의 안전 API에만 요청한다.

소스 장면에는 공개 참조 배치의 공급 트레일러, 압축기, 저·중·고압 저장 뱅크, 공통 헤더, 프리쿨러, 디스펜서 2기, 차량 2대, 벤트, 캐노피, 도로와 운영실이 포함된다. 충전 요청과 실제 유량에 따라 각 호스가 디스펜서 주차 위치와 차량 연결 위치를 전환한다. 서버 피드백에 따라 모든 가상 차단밸브, 환기팬, 저장 뱅크 냉각, 출입통제, 인원 대피, 화재 입력과 이상 설비 강조가 갱신된다. 시각 효과는 프레임마다 재생성하지 않고 기존 컴포넌트의 상태만 바꿔 화면 깜빡임과 메모리 누적을 줄인다.

명령 전송 성공을 실제 폐쇄로 표시하지 않는다. 서버 피드백에 따라 이동·폐쇄·실패 색상이 바뀐다. 용기 자체 누출은 밸브 차단만으로 임의 제거하지 않는다. 기존 서버의 훈련 사고 종료 규칙을 그대로 따른다. 재전송으로 사고 상태를 되살리지 않도록 표시 대상 바인딩에는 요청 순번을 적용한다.

## 데이터 계약

- `/api/integrations/unreal/scene`: 장치 ID, 기준 배치, 단위, 위치, 검지기와 카메라 좌표.
- `/api/integrations/unreal/config`: 플레이어 주소와 연결 규칙.
- `/api/integrations/unreal/session/default`: 한 조작석의 표시 실행 ID와 generation. POST에서 `run_id: null`은 표시 초기화만 한다.
- `/api/integrations/unreal/session/default/feedback`: Unreal이 실제 라벨에 적용한 설비별 값을 동일 sequence의 서버 프레임과 대조하는 진단 피드백. 공정 상태를 변경하지 않는다.
- `/api/simulations/{id}/visualization/snapshot`: 상태 전체 스냅샷.
- `/api/simulations/{id}/visualization/stream`: WebSocket 스냅샷 및 1초 heartbeat.
- `/api/simulations/{id}/safety/actions`: 기존 가상 조치 API. 신규 LLM 경로를 만들지 않는다.

좌표는 Three.js `(x,y,z)` 미터를 UE `(100*x,100*z,100*y)` 센티미터로 변환한다. 압력 MPa_abs, 온도 degC, 유량 g/s, 질량 kg, 거리 m를 그대로 사용한다. 결측은 null이다. 표시 API는 solver·HyRAM·LLM을 실행하지 않는다. 위험도는 이미 계산된 캐시를 제공하며, 켰을 때 기존 위험 API를 저빈도로 요청한다. 현재 위험도는 연간 사망 확률이 아닌 서버의 screening 지수다.

## 검증과 남은 작업

진행률은 `progress.json`의 수락 항목에서 `verified`의 비율이다. `source_ready`는 소스가 작성됐어도 UE 실행을 확인하기 전에는 완료로 세지 않는다. `scripts/report_unreal_progress.py`로 단계별 진행률을 출력한다.

기존 저·중·고압 뱅크, 압축기, 프리쿨러, 차량, 튜브 트레일러의 총 7개 GLB 자산을 `output/unreal/assets`에 생성했다. Khronos glTF Validator 2.0.0-dev.3.10 검증에서 오류·경고 0이다. Unreal 가져오기와 축/크기 검증은 별도로 필요하다. glTF는 미터/Y-up이고 UE는 센티미터/Z-up이므로 공식 glTF 가져오기 설정의 `import_scale=100`으로 단 한 번 변환한다. `/Game/HRS/Models`는 패키징 시 항상 cook된다. 재생성은 `scripts/export_unreal_assets.cjs`, 검증은 `scripts/validate_unreal_assets.cjs`, UE 가져오기는 `HRSUnreal/Scripts/import_reference_assets.py`를 사용한다. Playwright 모듈 경로는 `HRS_PLAYWRIGHT_MODULE`로 지정할 수 있다.

웹 연결 검증은 `scripts/verify_unreal_web.cjs`를 사용한다. 전용 로컬 API와 Pixel Streaming 서버를 먼저 실행한다. 테스트 페이지에서만 플레이어 설정을 대체하며 운영 환경변수는 변경하지 않는다. 실제 시뮬레이터의 뱅크 압력·질량과 표시 대상 변경·초기화 연결을 검증한다. UE 영상 검증은 아니며 보고서에도 명시한다. 공식 플레이어의 XR 자동 탐색은 데스크톱 시제품에서 불필요하므로 공식 API의 XR 컨트롤 비활성 옵션을 사용한다.

엔진을 실행한 뒤 실제 스트림 증거는 `node scripts/verify_unreal_video.cjs`로 수집한다. 이 검사는 플레이어 UI가 열린 사실만으로 통과하지 않으며, 1280×720 이상의 비디오가 5초 동안 실제로 전진해야 한다. 성공하면 `output/unreal/ue-video.json`과 화면 캡처를 남긴다. 이 한 번의 확인은 FPS·입력 지연·60분 안정성 검사를 대신하지 않는다.

성능 게이트는 전용 시뮬레이션을 스스로 생성·정지하는 `node scripts/verify_unreal_stream_quality.cjs <player-url> <api-url> <duration-s>`를 사용한다. 1080p, 평균 디코드 28.5 FPS 이상, 키 입력에서 서버 ESD 확인까지 1초 이하, 동일 sequence의 서버값과 Unreal 적용값 일치를 검사한다. 60분 게이트는 `duration-s`를 `3600`으로 지정한다. 결과의 브라우저 JS 힙은 보조 지표이며 UE 프로세스·GPU 메모리 측정을 대체하지 않는다.

같은 60분 동안 `./scripts/measure_unreal_process.ps1 -EngineRoot '<UE 경로>'`를 별도 터미널에서 실행해 UnrealEditor 작업 집합·전용 메모리·핸들 수를 기록한다. 반복 초기화는 `node scripts/verify_unreal_reset_reconnect.cjs`로 최소 3회의 새 실행→바인딩→가상 ESD→정지→표시 초기화를 검증한다. 두 검사는 전용 테스트 실행만 생성하며 운영 실행 ID를 재사용하지 않는다.

Python: `.venv\Scripts\python.exe -m pytest -q tests/test_unreal_visualization.py tests/test_api_frame_cursor.py tests/test_virtual_safety.py`.
JS: `node --test tests/unreal_view_state.test.mjs tests/risk_range_state.test.mjs tests/assistant_api_separation.test.mjs`.
UE 소스/매니페스트 일치: `.venv\Scripts\python.exe scripts/check_unreal_source_contract.py`.

계약, 좌표/단위, 결측·0값, 두 차량 분리, 명령/피드백, 이전 실행 초기화, 순번 역전, API/LLM 분리와 기존 위험거리 상태를 검증한다. 정적 계약 검사는 설비 14개, 검지기 24개, CCTV 5개와 조작 입력이 서버 매니페스트에서 빠지지 않았는지 확인한다. UE C++ 빌드·실사 품질·실제 입력 지연·30 FPS·60분 실행·엔진과 브라우저의 값 일치는 아직 검증 전이다. 복구 절차의 단계별 애니메이션과 실제 UE 렌더링 품질 보정은 후속 단계다.

API·Pixel Streaming 서버·3D 프로젝트는 단일 조작석 로컬 시제품 기준이다. 사내 다중 사용자 배포는 접근제어·세션 격리·HTTPS와 별도 GPU 용량 검증을 마친 뒤 수행한다.
