'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const inventory = require('../js/inventory-models.js');
const metrics = require('../js/inventory-metrics.js');

const pages = ['inventory-turnover-calculator.html','safety-stock-calculator.html','reorder-point-calculator.html','scm-diagnostic.html'];
function classes() { const set = new Set(); return {toggle(k, on) {on ? set.add(k) : set.delete(k);}, add(k) {set.add(k);}, remove(k) {set.delete(k);}, contains(k) {return set.has(k);}}; }
function tool(kind, inputs, dependencies = true) {
  const events = {}, button = {disabled:true}, output = {textContent:'',classList:classes()};
  const form = {dataset:{inventoryTool:kind},addEventListener:(type,fn)=>events[type]=fn,querySelectorAll:()=>inputs.map(value=>({value})),querySelector:()=>button};
  const document = {querySelector:()=>form,getElementById:()=>output};
  const window = dependencies ? {SCMInventory:inventory,SCMInventoryMetrics:metrics} : {};
  vm.runInNewContext(fs.readFileSync('js/inventory-tools.js','utf8'),{document,window,SCMInventory:inventory,SCMInventoryMetrics:metrics});
  return {events,button,output};
}
function submit(fn) { let prevented=false; fn({preventDefault(){prevented=true;}}); assert.equal(prevented,true); }
test('each calculator uses tested models and clears stale results on editing',()=>{
 for (const [kind,values,expected] of [
   ['turnover',['5000000','500000','365'],'10 раз за период; оценка 36,5 дней.'],
   ['safety',['120','100','7'],'Сценарная оценка: 140 единиц.'],
   ['reorder',['100','5','50'],'Расчётный порог: 550 единиц.'],
   ['turnover',['0','100','365'],'0 раз за период; дни не определены при нулевой себестоимости.'],
 ]) {
   const t=tool(kind,values);assert.equal(t.button.disabled,false);submit(t.events.submit);assert.equal(t.output.textContent,expected);
   t.events.input();assert.equal(t.output.textContent,'');
 }
 for (const [kind,values] of [['safety',['1','2','7']],['reorder',['1','0','1']],['turnover',['1','0','365']]]) {
   const t=tool(kind,values);submit(t.events.submit);assert(t.output.classList.contains('error'));assert.match(t.output.textContent,/Проверьте/);
 }
 assert.equal(tool('safety',['1','1','1'],false).button.disabled,true);
});
test('HTML pages are discoverable, indexable and related links point to existing pages',()=>{
 const sitemap=fs.readFileSync('sitemap.xml','utf8');const index=fs.readFileSync('calculators.html','utf8');
 for(const page of pages){
   const html=fs.readFileSync(page,'utf8');assert.match(html,new RegExp(`<link rel="canonical" href="https://scm-news\\.ru/${page}">`));
   assert(sitemap.includes(`https://scm-news.ru/${page}`));assert(index.includes(`href="${page}"`));
   assert.match(html,/<h1>/);assert.match(html,/type="submit" disabled/);assert.match(html,/role="status"/);
   for(const target of html.matchAll(/href="([^"#]+\.html)(?:#[^"]*)?"/g)) if (!/^https?:/.test(target[1])) assert(fs.existsSync(target[1]),`${page}: ${target[1]}`);
 }
});
test('diagnostic requires all answers, does not assign a score and builds links without HTML injection',()=>{
 const events={},button={disabled:true}, fields={stock:{value:'yes'},supply:{value:'unknown'},safety:{value:'review'},service:{value:'yes'}};
 const form={elements:fields,addEventListener:(k,f)=>events[k]=f,querySelector:()=>button};
 const element=()=>({children:[],textContent:'',classList:classes(),append(...x){this.children.push(...x);},replaceChildren(){this.children=[];this.textContent='';}});
 const output=element();const document={getElementById:id=>id==='scm-checklist'?form:output,createElement:tag=>({...element(),tag}),createTextNode:text=>({text})};
 vm.runInNewContext(fs.readFileSync('js/scm-diagnostic.js','utf8'),{document});assert.equal(button.disabled,false);
 submit(events.submit);assert.match(output.children[0].textContent,/проверить/);assert.equal(output.children[1].children.length,2);
 assert.equal(output.children[1].children[0].children[1].href,'reorder-point-calculator.html');
 fields.supply.value='';events.change();submit(events.submit);assert(output.classList.contains('error'));assert.match(output.textContent,/Ответьте/);
 for(const value of Object.values(fields))value.value='yes';submit(events.submit);assert.match(output.children[0].textContent,/не подтверждает/);assert.equal(output.children.length,1);
});
