# 수소충전소 상황별 대응 DB 및 적용 범위

이 문서는 `src/h2station/data/hazop.sqlite3`의 현재 정의와 `src/h2station/data/emergency_playbooks.json`의 대응 절차 연결 상태를 기록한다. 현장 비상계획이나 설비 제작사 운전절차를 대신하는 문서는 아니다. 모든 조치는 시뮬레이터 기반 의사결정 지원이며, 실제 차단 명령을 자동 실행하지 않는다.

## 현재 규칙 분석

- 공정 노드 23개, 센서 91개(가상 화염검지 9개 포함), 규칙 214개, 사고 계산 케이스 23개.
- 137개 규칙이 사실상 동일한 간단한 `권고대응` 문구를 공유해 누출, 과압, 센서 장애 등 서로 다른 상황을 구분하기 어려웠다.
- 모든 214개 규칙을 15개 대응 유형에 연결하고, 각 규칙에 고유한 센서·임계값·설비 위치를 반영한 5단계 대응 데이터를 저장했다. 사고 주입·안전밸브 상태도 해당 유형에 연결된다.

| 대응 유형 | 규칙 수 | 주된 신호·상황 |
|---|---:|---|
| 수소 누출·가스검지 상승 | 57 | 가스검지, 질량손실, 압력 급강하 |
| 저장·헤더·압축기 과압 | 23 | 뱅크 목표 초과, 헤더 과압, 토출 상한 |
| 차량 충전 과압·과열·급가압 | 22 | 차량 온도·압력·상승률, 충전 라인 이상 |
| 과유량·역류·유량 수지 불일치 | 19 | 체크밸브 역류, 과유량, 불일치 |
| 압축기 단계 과열·냉각 이상 | 19 | 단별 온도·압력 이상 |
| 안전계측 지연·고착·품질 불량 | 18 | 센서 갱신 지연 |
| 저압·무유량·막힘·공급 부족 | 15 | 공급 부족, 차압 증가, 운전 중 무유량 |
| 예냉·HTF 순환 성능 이상 | 13 | 열교환·HTF 이상 |
| 하역·충전 호스/연결부 이상 | 5 | 잔압, 압력 역전 |
| 벤트 배압·무명령 방출·역류 | 5 | 벤트 헤더 |
| ESD·PCV 폐쇄 후 유량 지속 | 4 | 차단 명령 후 유량 |
| 트레일러 공급·하역 경계 이상 | 3 | 하역 경계 |
| 외부 화재의 저장용기·차량 열 노출 | 11 | 차량 외부가열, 구역별 가상 화염검지 |
| 안전밸브 개방·벤트 방출 | 상태 기반 | `relief_valves_open` |
| 수소 제트화재·화염 확인 | 사고·질의 기반 | 명시적 화염 사고 또는 질문 |

각 절차는 **판단 신호 → 즉시 조치 → 안정화 확인 → 복귀 조건 → 예방·안전관리** 구조다. `src/h2station/data/hazop.sqlite3`의 각 `rules.payload`에 `대응유형`, `비상대응_단계`, `안전관리_방안`, `대응근거_출처`를 추가했고 `response_actions` 테이블에서도 규칙 ID로 조회할 수 있다. `GET /api/hazop/emergency-responses`는 15개 공통 절차와 214개 규칙별 단계·출처를 반환한다. 센서 임계값과 운전 게이트는 변경하지 않았다.

`PYTHONPATH=src python scripts/enrich_hazop_responses.py`로 원본 규칙 정의를 보존한 채 대응 단계만 재생성할 수 있다. 규칙별 문장은 공통 절차에 설비 위치, 센서 태그, 비교식, 지속시간, 복귀조건과 누출·화재·과압 등 유형별 확인 항목을 결합한다. 같은 대응 유형에 속한 여러 시나리오도 별도의 규칙 ID와 단계로 남는다.

## SAGA 연동

`POST /api/simulations/{job_id}/saga-analysis`는 최신 프레임의 활성 센서 규칙, 물리 누출, 사고 주입, 안전밸브 개방, 운전자 질문을 함께 판단한다. 활성 규칙을 공통 유형으로 합치지 않고 **시나리오별 단계**를 따로 선택한다. 축약된 조치를 현재 센서값·사고 계산값과 함께 LLM에 전달한다. LLM 응답 뒤에는 DB에 저장된 상세 절차를 Markdown으로 붙이므로 LLM 서버가 연결되지 않은 경보 상황에도 대응 내용이 남는다. 정상 상태의 정기 분석은 비상 절차를 표시하지 않는다. 운전자가 특정 가상 상황을 질문하면 실제 사고로 단정하지 않고 해당 절차를 제공한다. 가상 사고 생성·평가 응답에도 같은 절차가 들어간다.

같은 API 응답의 `analysis_answer`는 LLM 판단 요약, `response_guidance`는 단계별 구조화 절차다. SAGA 화면은 이를 **공통 초동대응 → 상황 확인 → 즉시 조치 → 안정화 확인 → 재가동 전 확인 → 예방·안전관리** 순서의 타임라인으로 표시한다. 기존 `answer`의 상세 Markdown은 다른 API 소비자를 위해 유지한다.

센서 상세 화면은 **활성 시나리오마다** 5단계 조치를 보여준다. 정상 센서는 비상대응 없이 시나리오별 예방·안전관리만 접어서 볼 수 있다. 선택 센서의 SAGA 분석에는 동시에 활성인 규칙별 조치가 전달된다. 기존 규칙의 중복된 간단한 `권고대응`은 LLM 프롬프트에서 제외했다.

근거에는 감지 노드·센서 태그·시나리오명 또는 사고 주입 대상·개방 밸브가 포함된다. 실제 누출 여부, 표본 피해영향 결과, 안전밸브 방출을 혼동하지 않도록 LLM 지침을 유지한다. 모의 피해영향의 관측 반경은 현장 대피거리로 확정하지 않는다.

## 자료와 한계

- [ISO 19880-1:2020](https://www.iso.org/standard/71940.html)은 기체 수소충전소의 설계·운전·점검·정비에 관한 적용 범위를 확인하는 데 사용했다. 유료 본문 조항을 보지 못했으므로 개별 조치의 직접 근거로 인용하지 않았다.
- [H2Tools 안전계획](https://h2tools.org/sites/default/files/Safety_Planning_for_H2_and_FC_Projects-Jan2020.pdf), [누출 검지](https://h2tools.org/bestpractices/hydrogen-properties-and-leak-detection-considerations/leak-detection), [화재 대응](https://h2tools.org/bestpractices/dealing-with-incidents/fire-protection-and-suppression), [사고 관리](https://h2tools.org/bestpractices/dealing-with-incidents/incident-management)는 감지·차단·환기·대피·훈련·복구 원칙에 사용했다.
- [EIGA 2024 긴급대응 워크숍](https://www.eiga.eu/wp-content/uploads/2024/01/MC.3_WILLIAMS-EIGA-WS-2024-FINAL.pdf)은 무화염 누출·제트화재·외부 화재 구분에 참고했다.
- [US DOE 안전 운전](https://www.energy.gov/cmei/fuels/current-safe-operating-practices)은 불활성 퍼지, 환기, 화염 검지 등의 원칙에 참고했다.
- [US DOT/PHMSA ERG 2024 Guide 115](https://www.phmsa.dot.gov/sites/phmsa.dot.gov/files/2024-04/ERG2024-Eng-Web-a.pdf)는 운송 중 가연성 가스 비상대응 자료다. 고정 충전소의 격리거리나 법적 요구사항으로 전용하지 않았다.
- [H2Tools 충전소 안전 실무](https://h2tools.org/bestpractices/gaseous-gh2-and-liquid-hydrogen-lh2-fueling-stations), [기체 수소 화재](https://h2tools.org/bestpractices/dealing-with-incidents/fire-protection-and-suppression/gaseous-hydrogen-fires), [화염검지](https://h2tools.org/bestpractices/hydrogen-properties-and-leak-detection-considerations/flame-detection)는 트레일러·저장·디스펜서의 격리와 화염 확인 단계에 반영했다.

개별 절차의 문장은 위 자료의 원칙을 설비·신호 맥락에 맞게 작성한 **프로젝트 운영안**이다. 특정 압력 설정값, 법정 이격거리, 수동 밸브 조작 순서 등을 새로운 표준 요구사항처럼 제시하지 않는다. 실제 적용 전 현장 책임자, 설비 제작사, 안전관리자 및 관할 소방과 대조·승인해야 한다.
