'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('js/resume-goals.js','utf8');
function setup(enabled, ym) {
  let click;
  const script=enabled ? source.replace('const RESUME_GOALS_ENABLED = false;', 'const RESUME_GOALS_ENABLED = true;') : source;
  vm.runInNewContext(script,{window:{ym},document:{addEventListener(type,fn){assert.equal(type,'click');click=fn;}}});
  return click;
}
function event(key, extra={}) {
  return {target:{closest(selector){assert.equal(selector,'a[data-resume-goal]');return {getAttribute(name){assert.equal(name,'data-resume-goal');return key;},get href(){throw Error('URL must not be read');}};}}, ...extra};
}
test('prepared resume goals remain disabled until separately reviewed',()=>{
  let calls=0;assert.equal(setup(false,()=>calls++),undefined);assert.equal(calls,0);
  for(const file of ['index.html','career.html']){
    const html=fs.readFileSync(file,'utf8');
    assert.doesNotMatch(html,/src="js\/resume-goals\.js"/);
    for(const [key,domain] of [['hh','surgut.hh.ru'],['zarplata','surgut.zarplata.ru']]) {
      assert.ok([...html.matchAll(/<a\b[^>]*>/g)].some(([tag])=>tag.includes(`data-resume-goal="${key}"`) && tag.includes(`href="https://${domain}/resume/`)),file+' '+key);
    }
  }
});
test('when explicitly enabled for tests sends fixed goal IDs only and preserves navigation',()=>{
  const calls=[];const click=setup(true,(...args)=>calls.push(args));
  click(event('hh'));click(event('zarplata'));click(event('__proto__'));click(event('private@example.test'));click(event('hh',{defaultPrevented:true}));click(event('hh',{button:2}));click({target:null});
  assert.deepEqual(calls,[[108401876,'reachGoal','resume_click_hh'],[108401876,'reachGoal','resume_click_zarplata']]);
  assert.doesNotMatch(JSON.stringify(calls),/private@example|https:/);
  assert.doesNotThrow(()=>setup(true,()=>{throw Error('blocked');})(event('hh')));
  assert.doesNotThrow(()=>setup(true,undefined)(event('hh')));
});
