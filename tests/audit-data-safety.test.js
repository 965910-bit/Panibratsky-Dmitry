'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function page(name) { return fs.readFileSync(`scm-platform/${name}.html`, 'utf8'); }
function extract(source,name) {
  const inline=source.match(new RegExp(`^    function ${name}\\([^\\n]*\\) \\{[^\\n]*\\}\\s*$`,'m'));
  const match=inline || source.match(new RegExp(`^    function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n    \\}`,'m'));
  assert.ok(match,name); return match[0];
}
function storage(initial) {
  const data=new Map(Object.entries(initial)), writes=[];
  return {data,writes,getItem:k=>data.get(k)??null,setItem:(k,v)=>{writes.push(['set',k]);data.set(k,v)},removeItem:k=>{writes.push(['remove',k]);data.delete(k)}};
}
test('legacy deletion never removes expanded form, templates, other branches or colliding category state', () => {
  const src=page('audit-registry');
  const data={scm_checklists_default:JSON.stringify({old:['x'],current_form:['x'],last_modified_old:['x']}),audit_registry_default:'[{"id":"1"}]',checklist_old_default:'old',checklist_last_modified_old_default:'shared',checklist_current_form_default:'current',checklist_custom_items_default:'custom',checklist_templates_default:'templates',checklist_old_other:'other'};
  const localStorage=storage(data);
  const ctx={localStorage,confirm:()=>true}; vm.createContext(ctx);
  vm.runInContext('let currentBranchId="default"; let renderAudits=()=>{},renderChecklists=()=>{};\n'+['saveAuditRegistry','removeLegacyChecklistState','deleteAll'].map(n=>extract(src,n)).join('\n'),ctx);
  ctx.removeLegacyChecklistState('old',{last_modified_old:['x']});
  assert.equal(localStorage.getItem('checklist_last_modified_old_default'),'shared');
  localStorage.setItem('checklist_old_default','old');
  ctx.deleteAll();
  assert.equal(localStorage.getItem('checklist_old_default'),null);
  assert.equal(localStorage.getItem('checklist_current_form_default'),'current');
  assert.equal(localStorage.getItem('checklist_custom_items_default'),'custom');
  assert.equal(localStorage.getItem('checklist_templates_default'),'templates');
  assert.equal(localStorage.getItem('checklist_old_other'),'other');
  assert.equal(localStorage.getItem('audit_registry_default'),'[]');
});

test('checklist export includes hidden answers without writing storage', () => {
  const src=page('checklists'), key='checklist_current_form_default';
  const localStorage=storage({[key]:JSON.stringify({hidden:{status:'yes',fact:'42'},visible:{status:'no',fact:'1'}})});
  let downloaded;
  const nodes={status_visible:{value:'yes'},fact_visible:{value:'2'}};
  const ctx={localStorage,document:{getElementById:id=>nodes[id]||null,createElement:()=>({click(){}})},Blob:class {constructor(parts){downloaded=JSON.parse(parts[0]);}},URL:{createObjectURL:()=> 'blob:preview'},Date};
  vm.createContext(ctx); vm.runInContext('let currentBranchId="default",customItems={},templates=[]; function getAllItems(){return {hidden:{},visible:{}};}\n'+extract(src,'exportData'),ctx);
  ctx.exportData();
  assert.equal(downloaded.currentFormState.hidden.fact,'42');
  assert.equal(downloaded.currentFormState.visible.fact,'2');
  assert.deepEqual(localStorage.writes,[]);
});

test('imports abort if branch changes, user cancels, data is invalid or legacy name collides', () => {
  for (const [name,fn] of [['checklists','importData'],['audit-registry','importRegistry']]) {
    const src=page(name), localStorage=storage({audit_registry_default:'old',checklist_current_form_default:'form'}), messages=[];
    let reader, approve=true;
    const ctx={localStorage,alert:s=>messages.push(s),confirm:()=>approve,FileReader:class {constructor(){reader=this} readAsText(){}}, renderAuditSections:()=>{},renderAudits:()=>{},renderChecklists:()=>{},saveAuditRegistry:a=>localStorage.setItem('audit_registry_default',JSON.stringify(a)),saveCustomItems:()=>{},saveTemplates:()=>{},getAllItems:()=>({})};
    vm.createContext(ctx); vm.runInContext('let currentBranchId="default",customItems={},templates=[],currentFilterIds=null;\n'+extract(src,fn),ctx);
    ctx[fn]('file'); vm.runInContext('currentBranchId="other"',ctx); reader.onload({target:{result:'{}'}});
    assert.match(messages.at(-1),/изменилась/); assert.deepEqual(localStorage.writes,[]);
    vm.runInContext('currentBranchId="default"',ctx); ctx[fn]('file'); approve=false; reader.onload({target:{result:JSON.stringify(name==='checklists'?{customItems:{}}:{audits:[]})}});
    assert.deepEqual(localStorage.writes,[]);
    ctx[fn]('file'); approve=true; reader.onload({target:{result:JSON.stringify(name==='checklists'?{templates:{}}:{audits:{}})}});
    assert.match(messages.at(-1),/Ошибка импорта/); assert.deepEqual(localStorage.writes,[]);
    if (name==='checklists') {
      vm.runInContext('let sectionsOrder=["one"];',ctx);
      ctx[fn]('file'); reader.onload({target:{result:JSON.stringify({customItems:{a:{section:'one',text:'overwrites built-in',inputType:'none'}}})}});
      assert.deepEqual(localStorage.writes,[]);
    }
    if (name==='audit-registry') {
      ctx[fn]('file'); reader.onload({target:{result:JSON.stringify({audits:[],checklists:[{name:'current_form',items:[],state:{},date:'2026-01-01'}]})}});
      assert.deepEqual(localStorage.writes,[]);
    }
  }
});

test('loading audit asks before replacing visible answers and registry link is handled', () => {
  const src=page('auditor'), localStorage=storage({audit_registry_default:JSON.stringify([{id:'1',type:'Плановый',statuses:{a:'yes'},facts:{a:'2'}}])});
  const nodes={status_a:{value:'no'},fact_a:{value:'5'}}; let approve=false;
  const ctx={localStorage,confirm:()=>approve,alert:()=>{},document:{getElementById:id=>nodes[id]||null,querySelectorAll:()=>[{value:'Плановый'}]},getAllItems:()=>({a:{}}),saveCurrentFormState:()=>{throw Error('must not save on cancellation')},updateAllScores:()=>{}};
  vm.createContext(ctx);vm.runInContext('let currentBranchId="default";\n'+extract(src,'loadAuditById'),ctx);
  ctx.loadAuditById('1'); assert.equal(nodes.status_a.value,'no'); assert.deepEqual(localStorage.writes,[]);
  approve=true; let saves=0; ctx.saveCurrentFormState=()=>saves++; ctx.loadAuditById('1');
  assert.equal(nodes.status_a.value,'yes'); assert.equal(nodes.fact_a.value,'2'); assert.equal(saves,1);
  assert.match(src,/new URLSearchParams\(window\.location\.search\)\.get\('load'\)/);
});
