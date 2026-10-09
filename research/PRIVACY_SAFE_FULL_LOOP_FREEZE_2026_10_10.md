# 비식별 full-loop 사전 고정 안내

이 절차는 원자료를 공개하지 않고도 충전 이벤트와 평가 코드를 결과를 보기 전에 잠그기 위한 단계다. **사전 고정은 검증 통과가 아니며, 안전거리나 안전 인증을 의미하지 않는다.**

## 순서

1. 원자료 보관자가 이벤트 시작을 0초로 맞춘 CSV를 최소 3건 준비한다.
2. `validate_privacy_safe_pilot_bundle`로 열 이름, 시간축, 수치 유한성, 질량 단조성을 검사한다.
3. 채널 역할 확인서를 작성한다. 최소 역할은 `elapsed_time_s`, `station_pressure_mpa`, `delivered_gas_temperature_c`, `protocol_phase`, `mass_or_transferred_mass`다.
4. 모델·평가 코드·프로토콜 파일을 선택한 뒤 `build_privacy_safe_freeze_manifest`를 실행한다.
5. 생성된 manifest의 SHA-256과 custodian의 “결과를 고정 전에 보지 않았다”는 확인을 보관한다.
6. 고정 이후에는 모델 파라미터를 조정하거나 성능이 좋은 이벤트만 골라내지 않는다.

## Python 예시

```python
from pathlib import Path
from h2station.privacy_safe_full_loop_intake import (
    build_privacy_safe_freeze_manifest,
)

manifest = build_privacy_safe_freeze_manifest(
    sorted(Path("pilot_events").glob("*.csv")),
    protocol_path="protocol.json",
    model_path="model.py",
    evaluator_path="evaluator.py",
    channel_roles={
        "elapsed_time_s": "event-relative logger time",
        "station_pressure_mpa": "station delivery boundary pressure",
        "delivered_gas_temperature_c": "delivery gas temperature",
        "protocol_phase": "controller phase label",
        "mass_or_transferred_mass": "calibrated mass-flow channel",
    },
)
```

저장소에서 반복 실행할 때는 다음 CLI를 사용할 수 있다. `roles.json`에는 위의
채널 역할 확인서만 넣고, 이벤트 CSV·프로토콜·모델·평가기는 원자료 보관자가
관리하는 경로를 지정한다.

```powershell
python scripts/freeze_privacy_safe_full_loop.py `
  --events pilot_events\event_001.csv pilot_events\event_002.csv pilot_events\event_003.csv `
  --protocol protocol.json `
  --model model.py `
  --evaluator evaluator.py `
  --channel-roles roles.json `
  --output research\pilot_freeze_manifest.json
```

출력 JSON은 결과 점수나 원시 경로를 저장하지 않고, 고정 시점의 코드·프로토콜·
이벤트 SHA-256과 역할·행 수만 보존한다.

manifest에는 원시 경로·파일명·행이 들어가지 않고, 이벤트별·코드별 SHA-256과 채널 역할 및 집계 개수만 남는다. 차량 압력·온도, 선택 뱅크, 프리쿨러, ESD 상태가 있으면 추가로 기록할 수 있지만, 이 단계만으로 full-loop 외부검증 게이트가 닫히지는 않는다.
