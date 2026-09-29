/* Shared SSE reader for the station and focused sensor conversations. */
(()=>{
  window.streamStationAnalysis=async(url,body,{signal,onStatus,onToken}={})=>{
    const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal});
    if(!response.ok){const failure=await response.json().catch(()=>({}));throw new Error(failure.detail||`분석 응답 ${response.status}`);}
    if(!response.body?.getReader)throw new Error('이 브라우저에서 분석 스트림을 읽을 수 없습니다.');
    const reader=response.body.getReader(),decoder=new TextDecoder();
    let buffer='',result=null;
    const consume=block=>{
      const lines=block.split(/\r?\n/),event=lines.find(line=>line.startsWith('event:'))?.slice(6).trim();
      const payloadText=lines.filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trim()).join('\n');
      if(!event||!payloadText)return;
      const payload=JSON.parse(payloadText);
      if(event==='status')onStatus?.(String(payload.text||''));
      else if(event==='token')onToken?.(String(payload.text||''));
      else if(event==='result')result=payload;
      else if(event==='error')throw new Error(payload.detail||'분석 스트림 오류');
    };
    try{
      while(true){
        const {value,done}=await reader.read();
        buffer+=decoder.decode(value||new Uint8Array(),{stream:!done});
        const blocks=buffer.split(/\r?\n\r?\n/);buffer=blocks.pop()||'';
        blocks.forEach(consume);
        if(done){if(buffer.trim())consume(buffer);break;}
      }
    }finally{reader.releaseLock();}
    if(!result)throw new Error('분석 결과가 전달되지 않았습니다.');
    return result;
  };
  window.revealStationText=async(text,render,valid=()=>true)=>{
    const chars=Array.from(String(text||'')),steps=Math.min(130,Math.max(24,Math.ceil(chars.length/22)));
    const size=Math.max(1,Math.ceil(chars.length/steps));
    for(let offset=size;offset<chars.length;offset+=size){
      if(!valid())return false;
      render(chars.slice(0,offset).join(''));
      await new Promise(resolve=>setTimeout(resolve,35));
    }
    if(!valid())return false;
    render(chars.join(''));
    return true;
  };
})();
