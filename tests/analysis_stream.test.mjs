import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

test('analysis stream reconstructs split UTF-8 tokens before the final result',async()=>{
  const events=[];
  const encoded=new TextEncoder().encode(
    'event: status\ndata: {"text":"계산 중"}\n\n'+
    'event: token\ndata: {"text":"중압 "}\n\n'+
    'event: token\ndata: {"text":"저장뱅크"}\n\n'+
    'event: result\ndata: {"answer":"중압 저장뱅크","impact_results":[1]}\n\n');
  const chunks=[encoded.slice(0,18),encoded.slice(18,31),encoded.slice(31,72),encoded.slice(72)];
  const body=new ReadableStream({start(controller){chunks.forEach(chunk=>controller.enqueue(chunk));controller.close();}});
  const context={window:{},TextDecoder,fetch:async()=>({ok:true,body})};
  runInNewContext(readFileSync(new URL('../web/analysis-stream.js',import.meta.url),'utf8'),context);
  const result=await context.window.streamStationAnalysis('/analysis',{},
    {onStatus:text=>events.push(['status',text]),onToken:text=>events.push(['token',text])});
  assert.deepEqual(events,[['status','계산 중'],['token','중압 '],['token','저장뱅크']]);
  assert.equal(result.answer,'중압 저장뱅크');
  assert.equal(result.impact_results.length,1);
});
