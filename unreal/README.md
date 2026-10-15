# 수소충전소 Unreal 전환 작업

## PyCharm 원클릭 실행

PyCharm에서 이 저장소를 연 뒤 실행 구성 목록의 **HRS Unreal Platform**을
선택하고 실행한다. Python API, Pixel Streaming, HRS Unreal 런타임을 순서대로
시작한 뒤 `http://127.0.0.1:8000/`을 연다. PyCharm의 중지 버튼은 이 실행이
시작한 하위 프로세스도 함께 종료한다. 필수 포트를 다른 프로세스가 점유한
경우에는 기존 프로세스를 먼저 중지하고 다시 실행한다.

기존 Python 계산 서버의 상태를 UE5에서 표시한다. 공정·HyRAM·HAZOP·LLM 계산은 기존 서버에 남는다. UE 5.8.3 Shipping 실행본에서 전체 참조 충전소 장면, 실시간 표시 API, 안전조치 입력 및 Pixel Streaming 영상 연결을 검증했다.

## 현재 설치 상태

2026-10-15: UE 5.8.3을 `C:\Program Files\Epic Games\UE_5.8`에 설치하고 `HRSUnrealEditor Win64 Development` 빌드를 완료했다. VS 2022 Build Tools 17.14, MSVC 14.38/14.44, MSBuild, Windows SDK 10.0.26100을 사용한다. 공식 Pixel Streaming Infrastructure의 `UE5.8` 브랜치와 UE 5.8에 함께 배포된 PixelStreaming 플러그인, Node.js 22.15.0을 사용한다. PixelStreaming2는 이 PC의 D3D12/NVENC 조합에서 시청자가 연결된 동안 private commit이 계속 증가하는 현상을 재현해 사용하지 않는다.

참조 GLB 7종을 Unreal에 가져와 8개 설비 인스턴스로 배치했으며, 각 인스턴스의 실제 바운드가 기준 치수의 75–125% 안에 드는지 검사했다. Shipping 실행본에서 1920×1080 WebRTC 영상, 서버-렌더러 계측값 일치, 브라우저 입력에서 서버 ESD 확인까지의 왕복 경로를 실제 실행으로 확인했다. 밸브·환기·냉각·출입 통제·대피·ESD·전체 정지의 대표 조치 행렬과 3회 초기화·재접속도 통과했다. 60분 연속 운전은 평균 29.93 FPS, 입력 확인 11 ms, 검은 화면·해상도 실패·급격한 평균 휘도 변화 각 0회였으며 UE 프로세스 종료나 지속 메모리 증가가 없었다.

환경 확인: 저장소 루트에서 `.venv\Scripts\python.exe scripts/check_unreal_environment.py` 실행. 별도 엔진 경로는 `HRS_UNREAL_ROOT`로 지정한다. 계정·비밀번호·API 키를 이 프로젝트에 넣지 않는다.

## 서버와 프로젝트 실행

1. UE 5.8.3 설치를 확인한다. 환경 검사는 `.venv\Scripts\python.exe scripts/check_unreal_environment.py`로 수행한다.
2. 계산 서버: 먼저 `$env:H2STATION_UNREAL_PLAYER_URL='http://127.0.0.1:18080/hrs-player.html'`를 설정하고 `.venv\Scripts\python.exe -m uvicorn h2station.api:app --app-dir src --host 127.0.0.1 --port 8000`을 실행한다. 소스나 체크아웃을 바꾼 뒤에는 기존 API 프로세스를 재사용하지 말고 재시작한다.
3. 엔진 경로를 지정하고 시제품 준비: `./scripts/start_unreal_pilot.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8' -Build -Bootstrap`. 고해상도 참조 GLB까지 가져와 현장 좌표에 배치하려면 먼저 웹 자산 내보내기·Khronos 검증을 실행한 뒤 `-ImportAssets -PlaceAssets`를 추가한다. 가져오기와 배치는 설비 ID 태그가 있는 기존 편집 액터를 덮어쓰지 않는다.
4. Pixel Streaming 서버: `./scripts/start_pixel_streaming.ps1`. 파일 `infrastructure-lock.json`의 버전과 커밋을 사용한다. 이 실행 스크립트는 로컬 PC에만 수신 포트를 연다.
5. UE 실행: `./scripts/start_unreal_pilot.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8' -Run -SignallingUrl 'ws://127.0.0.1:18888'`.
6. 기존 웹을 열면 Unreal 3D가 중앙 운영 화면에 자동 연결된다. 브라우저가 요구하면 영상 영역의 `CLICK TO START`를 한 번 누른다. `표준 3D로 전환`은 계산을 중지하지 않는다.

Win64 배포본은 `./scripts/build_unreal_release.ps1 -EngineRoot 'C:\Program Files\Epic Games\UE_5.8' -Configuration Shipping`으로 만든다. 이 명령은 소스 계약 검사, C++ 빌드, 맵·재질 생성, 검증된 GLB 가져오기, Interchange 기반 장면 배치와 실물 치수 범위 검사, cook·pak·archive를 순차 수행하고 실행 파일 SHA-256이 포함된 `hrs-unreal-build.json`을 남긴다. 패키지 실행은 `./scripts/start_packaged_unreal.ps1 -PackageDirectory '<패키지 폴더>'`를 사용한다. 실행 전에 해시를 다시 검사하며 기본값은 숨김 창, 로컬 API·Pixel Streaming 주소, 1080p/30fps, 단일 NVENC 세션, 20 Mbps 고정 목표 비트레이트와 D3D12-CUDA NVENC 상호운용이다. 이 장비의 RTX A4000에서 D3D12-CUDA 경로는 영상을 유지하면서 UE 5.7~5.8 NVENC 재설정에 따른 private commit 누적을 멈췄다. 다른 GPU에서 문제가 있으면 `-UseNvEncD3D12Cuda $false`로 끄고 별도 안정성 검증을 수행한다. 동일 실행 파일의 중복 실행은 기본적으로 차단한다. 현장 확인이 필요하면 `-Visible`을 추가한다.

UE 프로젝트 파일: `HRSUnreal/HRSUnreal.uproject`. 에셋 생성 스크립트는 이미 편집한 맵·재질을 덮어쓰지 않는다. 생성된 Content 및 바이너리는 Git에서 제외하고 소스·설정·생성 스크립트를 보관한다. 신규 UE 버전에 대한 검증은 별도로 수행한다.

## Pixel Streaming 서버 재현

공식 저장소를 `unreal/PixelStreamingInfrastructure`에 복제하고 lock 파일의 커밋으로 체크아웃한다. Node 공식 배포의 22.15.0 Windows x64 ZIP과 SHASUMS256.txt로 해시를 확인하여 `unreal/.tooling`에 풀어 둔다. 런타임과 서드파티 체크아웃은 Git에 올리지 않는다.

공식 저장소 루트에서 검증된 portable Node 22.15.0을 해당 셸 PATH에 추가하고 `npm ci --ignore-scripts --no-audit --no-fund`, `npm run build:all:cjs` 순서로 실행한다. Common, Signalling, 서버, 프런트엔드를 차례로 빌드한다. 설치 스크립트 실행 없이 필요한 TypeScript/webpack 빌드를 직접 실행한다. 업스트림 라이선스는 그대로 유지한다.

## 시제품 조작

왼쪽 버튼 드래그는 회전, 중간 버튼 드래그는 이동, 휠은 확대·축소다. 클릭 또는 1/2/3 키로 저/중/고압 뱅크를 선택한다. X는 선택 뱅크 입구 차단, Z는 출구 차단, E는 가상 ESD, F는 모든 공정 정지, R은 위험도 바닥, D는 표본 영향거리다. C는 CCTV 위치, G는 가스·화염 검지기 위치를 켜고 끈다. 기본값은 두 위치 표시 모두 꺼짐이다. 키 조작은 시뮬레이션 서버의 안전 API에만 요청한다.

소스 장면에는 공개 참조 배치의 공급 트레일러, 압축기, 저·중·고압 저장 뱅크, 공통 헤더, 프리쿨러, 디스펜서 2기, 차량 2대, 벤트, 캐노피, 도로와 운영실이 포함된다. 실사 참고 수준의 스테인리스 계장 배관·압력계·수동밸브·지지대, 디스펜서 표시창·비상정지·노즐 도크, 벤트 지지구조, 캐노피 보·조명·배수관, 방호 볼라드, 배수로, CCTV와 가스·화염검지기 하우징을 절차형 형상으로 보강했다. 운영실에는 외장 패널 이음·문틀·손잡이·차양·창호 프레임·배전함·외기팬·기초·홈통을 분리해 표현하고, 도로에는 보수 포장·정지선·횡단 표시·방향 표식·맨홀을 추가했다. 외곽 조경대에는 크기와 수관이 다른 나무, 화단, 조명과 일반화된 H2 분자 조형물을 배치했다. 작업자·방문객은 실제 사람 비례의 머리·몸통·팔다리·신발과 안전모·반사조끼로 구성되며, 동적 작업자는 기존 구역별 대피 상태와 함께 이동한다. 차량에는 문 이음·사이드실·와이퍼·안테나·번호판·반사판을 더해 도로 차량의 외형 단서를 보강했다. 캐노피 외장·띠장·마감재는 서로 떨어진 형상으로 만들어 깊이 충돌에 따른 모서리 반짝임을 방지한다. 충전 요청과 실제 유량에 따라 각 호스가 디스펜서 주차 위치와 차량 연결 위치를 전환한다. 서버 피드백에 따라 모든 가상 차단밸브, 환기팬, 저장 뱅크 냉각, 출입통제, 인원 대피, 화재 입력과 이상 설비 강조가 갱신된다. 시각 효과는 프레임마다 재생성하지 않고 기존 컴포넌트의 상태만 바꿔 화면 깜빡임과 메모리 누적을 줄인다.

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

기존 저·중·고압 뱅크, 압축기, 프리쿨러, 차량, 튜브 트레일러의 총 7개 GLB 자산을 `output/unreal/assets`에 생성했다. Khronos glTF Validator 2.0.0-dev.3.10 검증에서 오류·경고 0이다. glTF는 미터/Y-up이고 UE는 센티미터/Z-up이므로 공식 glTF 가져오기 설정의 `import_scale=100`으로 단 한 번 변환한다. `place_reference_scenes.py`는 8개 설비 인스턴스를 Station 맵에 배치하고 원본 치수 대비 75–125% 범위를 벗어나면 빌드를 중단한다. 설비 ID 태그를 통해 C++의 실시간 값·선택·표시 상태와 연결하며, 모델이 있을 때만 단순 형상을 숨긴다. `/Game/HRS/Models`와 `/Game/HRS/Scenes`는 패키징 시 항상 cook된다. 재생성은 `scripts/export_unreal_assets.cjs`, 검증은 `scripts/validate_unreal_assets.cjs`, UE 콘텐츠 가져오기는 `HRSUnreal/Scripts/import_reference_assets.py`, 맵 배치는 `HRSUnreal/Scripts/place_reference_scenes.py`를 사용한다. Playwright 모듈 경로는 `HRS_PLAYWRIGHT_MODULE`로 지정할 수 있다.

웹 연결 검증은 `scripts/verify_unreal_web.cjs`를 사용한다. 전용 로컬 API와 Pixel Streaming 서버를 먼저 실행한다. 테스트 페이지에서만 플레이어 설정을 대체하며 운영 환경변수는 변경하지 않는다. 실제 시뮬레이터의 뱅크 압력·질량과 표시 대상 변경·초기화 연결을 검증한다. UE 영상 검증은 아니며 보고서에도 명시한다. 공식 플레이어의 XR 자동 탐색은 데스크톱 시제품에서 불필요하므로 공식 API의 XR 컨트롤 비활성 옵션을 사용한다.

엔진을 실행한 뒤 실제 스트림 증거는 `node scripts/verify_unreal_video.cjs`로 수집한다. 이 검사는 플레이어 UI가 열린 사실만으로 통과하지 않으며, 1280×720 이상의 비디오가 5초 동안 실제로 전진해야 한다. 성공하면 `output/unreal/ue-video.json`과 화면 캡처를 남긴다. 이 한 번의 확인은 FPS·입력 지연·60분 안정성 검사를 대신하지 않는다.

얇은 캐노피 모서리나 고광택 배관의 국부 반짝임은 `node scripts/verify_unreal_static_edge_stability.cjs <player-url> 20`으로 확인한다. 정지 화면 상부를 0.25초 간격으로 비교해 큰 휘도 변화가 반복되는 픽셀 비율을 제한하며, 화면 전체 평균만 비교하는 장기 게이트가 놓칠 수 있는 작은 깊이 충돌·시간축 노이즈를 보완한다.

성능 게이트는 전용 시뮬레이션을 스스로 생성·정지하는 `node scripts/verify_unreal_stream_quality.cjs <player-url> <api-url> <duration-s>`를 사용한다. 1080p, 평균 디코드 28.5 FPS 이상, 키 입력에서 서버 ESD 확인까지 1초 이하, 동일 sequence의 서버값과 Unreal 적용값 일치를 검사한다. 60분 게이트는 `duration-s`를 `3600`으로 지정한다. 결과의 브라우저 JS 힙은 보조 지표이며 UE 프로세스·GPU 메모리 측정을 대체하지 않는다.

같은 60분 동안 편집기는 `./scripts/measure_unreal_process.ps1 -EngineRoot '<UE 경로>'`, 패키지는 `./scripts/measure_unreal_process.ps1 -TargetProcessId <PID>`를 별도 터미널에서 실행해 작업 집합·전용 메모리·핸들 수를 기록한다. 반복 초기화는 `node scripts/verify_unreal_reset_reconnect.cjs`로 최소 3회의 새 실행→바인딩→가상 ESD→정지→표시 초기화를 검증한다. 대표 안전조치 행렬은 `node scripts/verify_unreal_safety_actions.cjs`로 명령 수락과 실제 상태 피드백을 분리해 검사한다. 검증기는 전용 테스트 실행만 생성하며 운영 실행 ID를 재사용하지 않는다.

Python: `.venv\Scripts\python.exe -m pytest -q tests/test_unreal_visualization.py tests/test_api_frame_cursor.py tests/test_virtual_safety.py`.
JS: `node --test tests/unreal_view_state.test.mjs tests/risk_range_state.test.mjs tests/assistant_api_separation.test.mjs`.
UE 소스/매니페스트 일치: `.venv\Scripts\python.exe scripts/check_unreal_source_contract.py`.

계약, 좌표/단위, 결측·0값, 두 차량 분리, 명령/피드백, 이전 실행 초기화, 순번 역전, API/LLM 분리와 기존 위험거리 상태를 검증한다. 정적 계약 검사는 설비 14개, 검지기 24개, CCTV 5개와 조작 입력이 서버 매니페스트에서 빠지지 않았는지 확인한다. 실제 UE C++ Shipping 빌드·cook·pak·실행, 1920×1080 영상, 30초 동안 28.5 FPS 이상, 계측값 일치, ESD 입력과 대표 안전조치 8종은 통과했다. 최종 30초 품질 게이트는 30.14 FPS와 25 ms ESD 입력 응답을 기록했다. 별도의 60분 Shipping 게이트도 평균 29.93 FPS, 입력 확인 11 ms, 1,772개 시간 샘플에서 검은 화면·해상도 실패·급격한 휘도 변화 0회로 통과했다. 같은 시간의 UE 프로세스 측정에서 종료나 지속 메모리 증가가 없었다. 2026-10-15 주변 환경 상세화 후 7개 GLB 자산 검증 오류·경고 0건, 1080p 실제 영상, 전체 시각 상태·안전조치 회귀, 20초 국부 모서리 안정성 검사를 다시 통과했다.

API·Pixel Streaming 서버·3D 프로젝트는 단일 조작석 로컬 시제품 기준이다. 사내 다중 사용자 배포는 접근제어·세션 격리·HTTPS와 별도 GPU 용량 검증을 마친 뒤 수행한다.
