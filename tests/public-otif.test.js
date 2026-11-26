'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const install = require('../js/public-otif.js');
const model = require('../js/otif.js');
function setup(withModel = model) {
 const events = {}, button = {disabled:true}, output = {textContent:''};
 const form = {elements:{total:{value:'100'},completed:{value:'80'}},querySelector:()=>button,addEventListener:(name,handler)=>events[name]=handler};
 const document = {getElementById:id=>id==='otif-form'?form:id==='otif-output'?output:null};
 install(document, withModel);
 return {events,button,output,form};
}
test('public OTIF uses joint counts, clears stale output and rejects invalid input',()=>{
 const {events,button,output,form}=setup(); assert.equal(button.disabled,false);
 let prevented=false; const submit=()=>events.submit({preventDefault(){prevented=true;}});
 submit(); assert.equal(prevented,true); assert.match(output.textContent,/80 %/);
 form.elements.completed.value='0';events.input();assert.equal(output.textContent,'');submit();assert.match(output.textContent,/0 %/);
 for(const [completed,total] of [['101','100'],['1','0'],['-1','3'],['1.5','3'],['','2'],['1e2','100']]){
  form.elements.completed.value=completed;form.elements.total.value=total;submit();assert.match(output.textContent,/Введите целые/);
 }
 form.elements.completed.value='1';form.elements.total.value='3';submit();assert.match(output.textContent,/33,33 %/);
});
test('if model is unavailable the form remains disabled; no persistence or external requests',()=>{
 const s=setup(null);assert.equal(s.button.disabled,true);assert.deepEqual(Object.keys(s.events),[]);
 const js=fs.readFileSync('js/public-otif.js','utf8');assert.doesNotMatch(js,/localStorage|sessionStorage|fetch\(|XMLHttpRequest|\.ym\(|\.gtag\(/);
 const html=fs.readFileSync('scm-encyclopedia.html','utf8');
 assert.match(html,/id="otif-calculator"/);assert.match(html,/id="otif-output" class="result" role="status" aria-live="polite"/);
 assert.match(html,/src="js\/otif.js" defer><\/script><script src="js\/public-otif.js" defer/);
 assert.match(fs.readFileSync('calculators.html','utf8'),/href="scm-encyclopedia.html#otif-calculator"/);
});
