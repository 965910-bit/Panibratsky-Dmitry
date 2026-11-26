'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const model=require('../js/scm-metrics-practice.js');
test('forecast uses observation-level absolute errors and exposes zero actuals',()=>{
 const r=model.forecast('100;110\n200;180');
 assert.deepEqual(r,{count:2,actual:300,wape:10,mae:15,cfe:10,mape:10});
 const other=model.forecast('100;200\n100;0');
 assert.equal(other.wape,100); assert.equal(other.cfe,0); // offsets must not hide errors
 const zero=model.forecast('0;10\n100;100');
 assert.equal(zero.wape,10); assert.equal(zero.mape,null);
 assert.equal(model.forecast('0;1\n0;0').wape,null);
 assert.equal(model.forecast('1,5;2.5').mae,1);
});
test('freight is summed per section and payable denominators handled separately',()=>{
 assert.deepEqual(model.freight('4;100\n2;50\n0;50'),{distance:200,tonkm:500,load:2.5});
 assert.deepEqual(model.freight('1;0'),{distance:0,tonkm:0,load:null});
 assert.deepEqual(model.payable('120000','400','2'),{costPerInvoice:300,perFte:200});
 assert.deepEqual(model.payable('100','0','2'),{costPerInvoice:null,perFte:0});
 assert.deepEqual(model.payable('100','5','0'),{costPerInvoice:20,perFte:null});
 assert.equal(model.payable('100','2,5','1'),null);
});
test('input parser rejects malformed, adversarial and oversized data',()=>{
 for(const s of ['', '1;',';1','-1;2','1;2;3','1e2;1','Infinity;1','0x10;1','<img>;1','1000000001;2','1;2\n\n3;4',Array(101).fill('1;2').join('\n')]) {
  assert.equal(model.forecast(s),null,s);assert.equal(model.freight(s),null,s);
 }
 for(const value of ['','-1','1e9','Infinity','1000000001','1.1234567']) assert.equal(model.number(value),null);
});
test('forms initialise only when present; result clears on input and never uses HTML',()=>{
 const events={},button={disabled:true},output={textContent:''};
 const form={elements:{rows:{value:'100;110\n200;180'}},querySelector:()=>button,addEventListener:(type,fn)=>events[type]=fn};
 model.install({getElementById:id=>id==='practice-forecast'?form:id==='practice-forecast-output'?output:null});
 assert.equal(button.disabled,false);let prevented=false;events.submit({preventDefault(){prevented=true;}});
 assert(prevented);assert.match(output.textContent,/WAPE: 10 %/);
 form.elements.rows.value='1000000;1000000,001';events.submit({preventDefault(){}});assert.match(output.textContent,/1\.00e-7 %/);
 form.elements.rows.value='<img>;1';events.input();assert.equal(output.textContent,'');events.submit({preventDefault(){}});assert.match(output.textContent,/Проверьте ввод/);
 const code=fs.readFileSync('js/scm-metrics-practice.js','utf8');assert.doesNotMatch(code,/localStorage|sessionStorage|fetch\(|XMLHttpRequest|innerHTML|\.ym\(|\.gtag\(/);
 const page=fs.readFileSync('scm-metrics.html','utf8');assert.match(page,/<noscript>/);assert.match(page,/src="js\/scm-metrics-practice.js" defer/);
 for(const id of ['practice-forecast','practice-freight','practice-payable']) {
  const formHtml=page.match(new RegExp(`<form id="${id}">([\\s\\S]*?)</form>`))[1];
  assert.match(formHtml,/<button type="submit" disabled>/);assert.match(formHtml,/role="status" aria-live="polite"/);
 }
});
