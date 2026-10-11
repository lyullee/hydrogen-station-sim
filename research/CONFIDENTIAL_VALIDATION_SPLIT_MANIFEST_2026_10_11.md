import json,hashlib
from pathlib import Path
root=Path('.')
refs=[
 'research/confidential_operational_envelope_holdout_replay_2026_10_06.json',
 'research/confidential_station_cascade_sequence_holdout_2026_10_08.json',
 'research/confidential_station_recharge_pressure_forecast_holdout_2026_10_08.json',
 'research/confidential_station_lifecycle_pressure_alignment_holdout_2026_10_09.json',
 'research/independent_component_holdout_reanalysis_2026_10_11.json',
]
def sha(p): return hashlib.sha256((root/p).read_bytes()).hexdigest()
out={
 'schema_version':1,
 'artifact_type':'confidential_validation_split_manifest',
 'recorded_at':'2026-10-11',
 'status':'frozen_scope_manifest',
 'privacy':{
  'source_identifiers_published':False,'source_paths_published':False,
  'source_filenames_published':False,'source_headers_published':False,
  'raw_rows_persisted':False,'absolute_timestamps_published':False,
  'calendar_dates_published':False,'site_company_location_manufacturer_published':False,
 },
 'owner_station_side_split':{
  'source_scope':'33 owner-controlled station CSV files; de-identified and retained locally',
  'deduplicated_rows':56854143,
  'partition_rule':'episode/time order; calibration prefix and later untouched suffix; no random row mixing',
  'cohorts':[
   {'id':'pressure_boundary','calibration_points':998,'holdout_points':30,'holdout_duration_s':1755.0,'artifact':'research/confidential_operational_envelope_holdout_replay_2026_10_06.json'},
   {'id':'cascade_sequence','calibration_pairs':8106,'holdout_pairs':3664,'artifact':'research/confidential_station_cascade_sequence_holdout_2026_10_08.json'},
   {'id':'recharge_pressure_forecast','calibration_cases':1024,'holdout_cases':394,'artifact':'research/confidential_station_recharge_pressure_forecast_holdout_2026_10_08.json'},
   {'id':'lifecycle_alignment_negative_check','calibration_role':'development prefix only','holdout_role':'later suffix; negative result retained','artifact':'research/confidential_station_lifecycle_pressure_alignment_holdout_2026_10_09.json'},
  ],
  'fit_uses_holdout':False,
  'default_model_parameters_changed_after_holdout':False,
  'claim_label':'same_site_temporal_holdout',
 },
 'public_component_split':{
  'source_scope':'open Type-IV tank measurements',
  'partition_rule':'lab_test_number modulo 3 equals 0 reserved before outcome inspection',
  'calibration_cases':23,'holdout_cases':12,'excluded_mass_closure_cases':1,
  'artifact':'research/independent_component_holdout_reanalysis_2026_10_11.json',
  'claim_label':'independent_component_holdout',
 },
 'station_to_vehicle_full_loop':{
  'status':'not_available_in_rights_cleared_machine_readable_form',
  'required_channels':['station/dispenser pressure and temperature','vehicle/receptacle pressure and temperature','common elapsed-time axis','mass flow or transferred mass','protocol and reuse rights'],
  'decision':'excluded_from_current_goal_and_reported_as_limitation',
  'independent_external_validation_supported':False,
 },
 'integrity':{
  'referenced_artifacts_sha256':{p:sha(p) for p in refs},
  'raw_private_data_published':False,
  'post_outcome_refit_allowed':False,
 },
 'decision':{
  'same_site_station_side_holdout_supported':True,
  'independent_component_holdout_supported':True,
  'independent_external_full_loop_validation_supported':False,
  'full_loop_external_validation_gate_closed':False,
 },
 'claim_boundary':'The owned data are split into chronology-preserving same-site station-side holdouts and the public Type-IV data provide an independent component holdout. Neither partition supports a claim of independent external station-to-vehicle validation. The unavailable synchronized station-to-vehicle archive is a stated limitation and remains outside the current target.',
}
Path('research/confidential_validation_split_manifest_2026_10_11.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY
@'
# 보유자료 검증 분할 명세 — 2026-10-11

이 명세는 공개하지 않는 소유자 통합운전자료를 보정과 시간순 후속 holdout으로 분리한 규칙을 고정한다. 행을 무작위로 섞지 않고 episode/시간 순서를 보존해 같은 충전 사이클의 인접 행이 양쪽에 들어가는 누수를 막는다.

## 적용된 분할

- **소유자 station-side 자료**: 33개 CSV에서 중복 제거 후 56,854,143개 행. 압력 경계는 보정 998점·후속 holdout 30점, 캐스케이드 전이는 보정 8,106쌍·holdout 3,664쌍, 재충전 압력 예측은 보정 1,024건·holdout 394건이다. lifecycle counter 정렬은 음성 결과를 보존하며 보정이나 런타임 승격에 사용하지 않는다.
- **공개 Type-IV 구성요소 자료**: 결과를 보기 전에 `lab_test_number % 3 == 0`을 holdout으로 예약했다. 보정 23건, holdout 12건, 질량 폐쇄 실패 1건이다.

보정에 holdout 결과를 사용하지 않았고, holdout을 본 뒤 기본 모델 파라미터를 바꾸지 않았다. 원시 행, 태그, 절대 날짜와 사업장 식별자는 저장소에 남기지 않고 참조 산출물의 SHA-256만 기록한다.

## 논문에서의 명칭과 한계

소유자 자료는 **동일 사이트 시간순 station-side holdout**으로 부른다. 데이터 소유자가 외부 기관이 아니므로 이를 독립 외부검증이라고 부르지 않는다. 공개 Type-IV 자료는 차량이 아닌 탱크 구성요소의 독립 holdout으로만 보고한다.

동기화된 station-to-vehicle 원자료(공통 시간축의 디스펜서·차량 압력/온도·질량유량, 프로토콜과 재사용 권리 포함)는 현재 권리 확인이 끝난 기계 판독 묶음으로 확보되지 않았다. 따라서 완전한 station-to-vehicle 외부검증은 목표와 결과에서 제외하고 Data availability/Limitations에 명시한다.

상세 기계 판정과 참조 산출물 해시는 `confidential_validation_split_manifest_2026_10_11.json`에 기록한다.
