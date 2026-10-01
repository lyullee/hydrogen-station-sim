/* A shared bridge for simulated actions from sensor and SAGA panels. */
(()=>{
  const jobId=()=>window.getStation3DState?.()?.activeJobId||window.getRemoteJobId?.()||new URLSearchParams(location.search).get('job');
  window.executeVirtualSafetyAction=async(action)=>{
    const id=jobId();
    if(!id)throw new Error('먼저 공정 모니터링을 시작하세요.');
    const response=await fetch(`/api/simulations/${encodeURIComponent(id)}/safety/actions`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({kind:action.kind,target:action.target,note:action.label||''})
    });
    const result=await response.json();
    if(!response.ok)throw new Error(result.detail||`조치 명령 오류 (${response.status})`);
    window.dispatchEvent(new CustomEvent('station-safety-action',{detail:{jobId:id,action:result.action}}));
    return result.action;
  };
  window.mountVirtualActionButtons=(host,actions)=>{
    if(!actions?.length)return;
    const group=document.createElement('div');group.className='virtual-action-buttons';
    const status=document.createElement('small');status.className='virtual-action-status';
    for(const action of actions){
      const button=document.createElement('button');button.type='button';button.textContent=action.label;
      button.addEventListener('click',async()=>{
        button.disabled=true;status.textContent=`${action.label} · 명령 전송 중`;
        try{const result=await window.executeVirtualSafetyAction(action);
          status.textContent=`${action.label} · ${result.status==='commanded'?'이동 중 · 피드백 확인 대기':result.status==='confirmed'?'완료':'조치 실패'} · 리모콘에서 세부 상태 확인`;
        }catch(error){status.textContent=`조치 실패 · ${error.message}`;}
        finally{button.disabled=false;}
      });group.append(button);
    }
    group.append(status);host.append(group);
  };
})();
