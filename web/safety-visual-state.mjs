const banks={low:'저압',medium:'중압',high:'고압'};
const coolingNames={...banks,dispenser_1:'1번 충전호스·차량',dispenser_2:'2번 충전호스·차량'};
const fireNames={'dispenser.hose':'1번 충전호스','dispenser_2.hose':'2번 충전호스','vehicle.tank':'1번 차량탱크','vehicle_2.tank':'2번 차량탱크'};
const zones={storage:'저장뱅크',compressor:'압축기',dispenser:'충전 구역',unloading:'하역 구역',cooler:'냉각 구역'};
export function safetyVisualState(safety, faults=[]){
  if(!safety)return {signature:'',badges:[],spraying:[],ventilating:[]};
  const badges=[],spraying=[],ventilating=[];
  if(safety.esd_requested)badges.push('ESD 차단 요청');
  for(const [bank,value] of Object.entries(safety.cooling||{})){
    const label=coolingNames[bank]||bank;
    if(value.fault)badges.push(`${label} 살수 고장 · 가동 불가`);
    else if(value.running){spraying.push(bank);badges.push(value.post_cooling_remaining_s != null ? `${label} 잔열 냉각 · ${Math.ceil(value.post_cooling_remaining_s)}초 후 자동 종료` : `${label} 냉각·살수 가동`);}
    else if(value.auto_stopped)badges.push(`${label} 잔열 냉각 완료 · 자동 종료`);
    else if(value.commanded)badges.push(`${label} 살수 명령 · 작동 대기`);
  }
  for(const [zone,value] of Object.entries(safety.ventilation||{})){
    if(value.fault)badges.push(`${zones[zone]||zone} 환기 고장`);
    else if(value.running){ventilating.push(zone);badges.push(`${zones[zone]||zone} 환기 가동`);}
    else badges.push(`${zones[zone]||zone} 환기 정지`);
  }
  for(const [name,value] of Object.entries(safety.valves||{})){
    if(value.status==='failed')badges.push(`${value.label||name} 조치 실패`);
    else if(value.status==='moving')badges.push(`${value.label||name} 이동 중`);
    else if(name.startsWith('vent.')&&value.actual_open)badges.push(`${banks[name.split('.')[1]]||name} 벤트 열림`);
    else if(!name.startsWith('vent.')&&!value.actual_open)badges.push(`${value.label||name} 닫힘`);
  }
  for(const [zone,on] of Object.entries(safety.power_isolated||{}))if(on)badges.push(`${zones[zone]||zone} 전원 차단`);
  for(const [zone,on] of Object.entries(safety.access_restricted||{}))if(on)badges.push(`${zones[zone]||zone} 출입 통제`);
  for(const target of new Set(Object.values(safety.fire_response||{}).map(row=>row.target))){
    const row=currentFireResponse(safety,target);
    const label=fireNames[row.target]||banks[row.target?.split('.')[1]]||row.target;
    badges.unshift(row.status==='ended'?`${label} 화재 입력 종료 · 잔열 냉각 확인`:row.status==='extinguished'?`${label} 훈련 화재 소멸 · ${safety.recovery_approved?'복구 승인 완료':'복구 점검 대기'}`:`${label} 훈련 화재 ${Math.round(row.intensity*100)}%${row.status==='suppressing'?' · 살수로 감소 중':''}`);
  }
  if(faults.some(f=>f.startsWith('external-fire:'))&&!Object.keys(safety.fire_response||{}).length)badges.push('외부 화재 입력 유지');
  else if(safety.residual_hazard?.status==='monitoring')badges.push('사고 입력 종료 · 잔류 위험 확인 중');
  if(safety.diagnostic)badges.push('복구 시험 진행 중');
  if(safety.purge_bank)badges.push(`${banks[safety.purge_bank]||safety.purge_bank} 퍼지 진행 중`);
  if(safety.responders_notified)badges.push('대응조직 통보 완료');
  if(safety.recovery_approved)badges.push('재가동 승인 완료');
  return {signature:JSON.stringify([badges,spraying,ventilating,safety.power_isolated,safety.access_restricted,safety.esd_requested]),badges,spraying,ventilating};
}

export function currentFireResponse(safety,target){
 const rows=Object.values(safety?.fire_response||{}).filter(row=>row.target===target);
 return rows.filter(row=>['active','suppressing'].includes(row.status)).at(-1)||rows.at(-1);
}
