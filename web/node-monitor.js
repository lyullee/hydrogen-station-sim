/* HAZOP sensor tags are the single source for per-node P/T/F telemetry. */
(()=>{
  let catalog=null,selected='N13';
  const $=id=>document.getElementById(id);
  const metrics=[['P','압력','MPa'],['T','온도','°C'],['F','유량','g/s']];
  const sensors=(node,prefix)=>catalog?.sensors?.filter(s=>s.node_id===node&&s.sensor_id?.startsWith(prefix+'T-'))||[];
  function series(metric,node=selected){
    const definition=metrics[metric]||metrics[0],frames=window.getStation3DState?.()?.result?.hazop?.frames||[];
    const candidates=sensors(node,definition[0]);
    const tag=candidates.find(s=>frames.some(f=>f?.signals?.[s.sensor_id]?.quality==='GOOD'))?.sensor_id||candidates[0]?.sensor_id;
    return {tag:tag||null,label:definition[1],unit:definition[2],values:frames.map(f=>{const signal=f?.signals?.[tag];return signal?.quality==='GOOD'&&Number.isFinite(signal.value)?signal.value:null;})};
  }
  function draw(canvas,values,times,index){
    const w=canvas.clientWidth,h=canvas.clientHeight;if(w<2||h<2)return;
    const scale=Math.min(devicePixelRatio||1,2);canvas.width=w*scale;canvas.height=h*scale;const ctx=canvas.getContext('2d');ctx.scale(scale,scale);
    const end=times[index]||0;let start=0;while(start<index&&times[start]<end-120)start++;
    const valid=values.slice(start,index+1).filter(Number.isFinite);if(!valid.length)return;
    const low=Math.min(...valid),high=Math.max(...valid),pad=Math.max(.1,(high-low)*.2),lo=low-pad,hi=high+pad;
    ctx.strokeStyle='#dce8e6';ctx.lineWidth=1;for(const y of [5,h/2,h-5]){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
    ctx.strokeStyle='#208d7b';ctx.lineWidth=2;ctx.beginPath();let started=false;
    for(let i=start;i<=index;i++){if(!Number.isFinite(values[i])){started=false;continue;}const x=2+(times[i]-times[start])/Math.max(.001,end-times[start])*(w-4),y=h-5-(values[i]-lo)/(hi-lo)*(h-10);if(started)ctx.lineTo(x,y);else{ctx.moveTo(x,y);started=true;}}ctx.stroke();
  }
  function render(){
    if(!$('wallNodeSelect')||!catalog)return;
    const runtime=window.getStation3DState?.(),times=runtime?.result?.series?.time_s||[],index=runtime?.index??0;
    for(let n=0;n<3;n++){
      const data=series(n),latest=data.values[index],value=$(`wallTrendValue${n}`),header=$(`wallTag${n}`);
      value.textContent=Number.isFinite(latest)?`${latest.toFixed(n===2?2:1)} ${data.unit}`:'미연결';
      header.textContent=data.tag||'센서 없음';
      draw($(`wallTrend${n}`),data.values,times,index);
    }
  }
  function mount(){
    const wall=$('wallTrend0');if(!wall)return;
    const title=document.querySelector('.wall-trend-title');
    const select=document.createElement('select');select.id='wallNodeSelect';select.setAttribute('aria-label','추세 설비 노드 선택');title.insertBefore(select,title.querySelector('button'));
    const detailSelect=document.createElement('select');detailSelect.id='detailNodeSelect';detailSelect.setAttribute('aria-label','상세 추세 설비 노드 선택');document.querySelector('.chart-panel .trend-selector')?.prepend(detailSelect);
    for(let i=0;i<3;i++){$(`wallTrendValue${i}`).insertAdjacentHTML('beforebegin',`<small class="wall-trend-tag" id="wallTag${i}">—</small>`);}
    fetch('/api/hazop/catalog').then(r=>r.json()).then(data=>{
      catalog=data;
      for(const node of data.nodes){const label=node['설비_라인']||node.node_id;for(const input of [select,detailSelect])input.add(new Option(`${node.node_id} · ${label}`,node.node_id));}
      select.value=selected;detailSelect.value=selected;render();
    }).catch(()=>{select.add(new Option('센서 목록 연결 실패',''));});
    for(const input of [select,detailSelect])input.addEventListener('change',()=>{selected=input.value;select.value=selected;detailSelect.value=selected;render();window.drawStationTrend?.();});
    window.addEventListener('station-frame',render);window.addEventListener('wall-resize',render);
  }
  window.nodeMonitor={series,get selectedNode(){return selected;},get catalog(){return catalog;},selectNode(id){if(catalog?.nodes?.some(n=>n.node_id===id)){selected=id;if($('wallNodeSelect'))$('wallNodeSelect').value=id;render();}}};
  window.addEventListener('station-layout-ready',mount,{once:true});
})();
