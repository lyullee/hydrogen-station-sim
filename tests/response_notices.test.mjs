import test from 'node:test';
import assert from 'node:assert/strict';
import {createResponseNotices} from '../web/response-notices.mjs';
test('dismissed messages stay cleared across identical telemetry frames',()=>{
 const state=createResponseNotices(),labels=['환기 가동','복구 승인 완료'];
 assert.deepEqual(state.read('one',labels),labels);state.dismiss();
 assert.deepEqual(state.read('one',labels),[]);assert.deepEqual(labels,['환기 가동','복구 승인 완료']);
});
test('new states appear and a state can reappear after changing away',()=>{
 const state=createResponseNotices();state.read('one',['환기 가동']);state.dismiss();
 assert.deepEqual(state.read('one',['환기 정지']),['환기 정지']);
 assert.deepEqual(state.read('one',['환기 가동']),['환기 가동']);
});
test('new job and complete reset discard the dismissal history',()=>{
 const state=createResponseNotices();state.read('one',['밸브 닫힘']);state.dismiss();
 assert.deepEqual(state.read('two',['밸브 닫힘']),['밸브 닫힘']);state.dismiss();state.reset();
 assert.deepEqual(state.read('two',['밸브 닫힘']),['밸브 닫힘']);
});
