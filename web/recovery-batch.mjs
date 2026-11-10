export async function runRecoveryBatch({read,issue,progress=()=>{},cancelled=()=>false,pause=()=>new Promise(r=>setTimeout(r,350)),banks=['low','medium','high']}){
 const bankLabel={low:'저압',medium:'중압',high:'고압'};
 const check=()=>{if(cancelled())throw new Error('일괄 점검을 중지했습니다. 완료한 조치는 유지됩니다.');};
 let state=await read();
 if((state.active_incidents||[]).length||Number(state.current_metrics?.total_leak_flow_g_s||0)>.01||Number(state.current_metrics?.gas_max_volpct_h2||0)>=.2)throw new Error('사고·누출·잔류 가스가 남아 있습니다. 안정화 후 일괄 점검을 실행하세요.');
 if(Object.values(state.cooling||{}).some(v=>v.running))throw new Error('잔열 냉각이 진행 중입니다. 냉각 종료 후 일괄 점검을 실행하세요.');
 const step=async(label,kind,target)=>{
  check();progress(label);const action=await issue(kind,target,label);
  const deadline=Date.now()+60000;
  while(true){check();state=await read();const current=(state.actions||[]).find(a=>a.id===action.id)||action;
   if(current.status==='failed')throw new Error(label+' 실패: '+(current.note||'설비 상태와 사건 기록을 확인하세요.'));
   if(current.status==='confirmed')break;
   if(Date.now()>deadline)throw new Error(label+' 확인 시간이 초과되었습니다. 계산 및 설비 상태를 확인하세요.');
   await pause();
  }
 };
 await step('모든 공정 정지','operation.stop','all');
 await step('ESD 차단 유지','esd.trip','station');
 for(const bank of banks){for(const side of ['inlet','outlet'])await step(bankLabel[bank]+' 뱅크 격리','valve.close',`bank.${bank}.${side}`);await step(bankLabel[bank]+' 벤트 닫기','vent.close','vent.'+bank);}
 await step('원인 제거 확인','recovery.record','source_removed');
 await step('누출 없음 확인','recovery.record','leak_repaired');
 for(const bank of banks)await step(bankLabel[bank]+' 기밀시험','tightness.test',bank);
 await step('검지기 시험','detector.test','all');
 await step('밸브 기능시험','valve.test','all');
 for(const bank of banks)await step(bankLabel[bank]+' 라인 퍼지','purge.run',bank);
 for(const bank of banks)await step(bankLabel[bank]+' 단계 재가압','pressure.test',bank);
 await step('감독자 모의 확인','recovery.record','supervisor_approval');
 await step('재가동 승인 및 PLC 확인','restart.approve','station');
 if(!state.recovery_approved)throw new Error('PLC 재가동 승인이 확인되지 않았습니다.');
 progress('일괄 복구 점검 완료 · 재가동 승인 완료. 밸브 개방과 공정 시작은 별도로 조작하세요.');
 return state;
}
