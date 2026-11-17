'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function page(name) { return fs.readFileSync(`scm-platform/${name}.html`, 'utf8'); }
function extract(source, name) {
  const oneLine = source.match(new RegExp(`^    function ${name}\\([^\\n]*\\) \\{[^\\n]*\\}\\s*$`, 'm'));
  if (oneLine) return oneLine[0];
  const m = source.match(new RegExp(`^    function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n    \\}`, 'm'));
  assert.ok(m, name); return m[0];
}
function storage(initial = {}) {
  const data = new Map(Object.entries(initial)), writes = [];
  return {data, writes, getItem: k => data.get(k) ?? null, setItem: (k, v) => {writes.push(k); data.set(k, v);}};
}
function harness(source, functions, initial = {}) {
  const nodes = new Map(), localStorage = storage(initial), alerts = [];
  const document = {getElementById: id => nodes.get(id) || null, querySelector: () => ({value:'Плановый'})};
  const ctx = {document, localStorage, alert: s => alerts.push(s), confirm: () => true, Date, Math};
  vm.createContext(ctx);
  vm.runInContext(`let currentBranchId = 'default'; const masterItems = {a:{section:'one',text:'Встроенный',inputType:'number',target:100,condition:'greater',recommend:'≥100'}, b:{section:'two',text:'Скрытый',inputType:'none'}, c:{section:'one',text:'Пользовательский',inputType:'number',target:10,condition:'less'}}; let customItems = {}; let sectionTitles = {one:'Первая',two:'Вторая'};\n` + functions.map(f => extract(source, f)).join('\n'),ctx);
  return {ctx, nodes, localStorage, alerts};
}

test('both forms are initially unassessed, disable scoring and task creation, preserve filtered answers', () => {
  for (const [name, prefix] of [['auditor','audit'],['checklists','checklist']]) {
    const source = page(name);
    assert.match(source, /value="unknown" selected>Не оценено/);
    assert.doesNotMatch(source, /function isFactCompliant|function computeSectionProgress|addTaskToRegistry/);
    assert.match(source, /Автоматические оценки и создание поручений приостановлены/);
    assert.match(source, /customItems = saved \? JSON\.parse\(saved\) : \{\}/);
    const saved = JSON.stringify({b:{status:'yes',fact:''},a:{status:'yes',fact:'99'}});
    const key=`${prefix}_current_form_default`;
    const {ctx,nodes,localStorage}=harness(source,['getAllItems','saveCurrentFormState','loadCurrentFormState','updateAllScores'],{[key]:saved});
    nodes.set('status_a',{value:'unknown'}); nodes.set('fact_a',{value:''});
    ctx.loadCurrentFormState(); assert.equal(nodes.get('fact_a').value,'99');
    ctx.updateAllScores(); assert.deepEqual(localStorage.writes, []);
    nodes.get('fact_a').value='0'; ctx.saveCurrentFormState();
    const state=JSON.parse(localStorage.getItem(key));
    assert.equal(state.a.fact,'0'); assert.equal(state.b.status,'yes');
    assert.deepEqual(localStorage.writes,[key]);
  }
  assert.match(page('checklists'), /id="createTasksFromPendingBtn" disabled/);
  assert.match(page('auditor'), /id="calculateBtn" disabled/);
});

test('new audit stores only manual answers and never writes tasks or old audit records', () => {
  const source = page('auditor');
  const old = {id:'old',type:'Плановый',totalPercent:89,nonConformances:[{text:'old'}]};
  const key='audit_registry_default';
  const {ctx,nodes,localStorage,alerts}=harness(source,['getAllItems','saveAuditToRegistry'],{[key]:JSON.stringify([old]),tasks_registry_default:'[{"id":"old"}]',planner_tasks_default:'{"old":[]}' });
  nodes.set('status_a',{value:'yes'}); nodes.set('fact_a',{value:'0'});
  nodes.set('status_c',{value:'no'}); nodes.set('fact_c',{value:'200'});
  ctx.saveAuditToRegistry(true);
  const audits=JSON.parse(localStorage.getItem(key)), entry=audits[1];
  assert.deepEqual(audits[0],old);
  assert.equal(entry.method,'manual-responses-v1'); assert.equal(entry.totalPercent,null);
  assert.deepEqual(entry.sectionScores,{}); assert.deepEqual(entry.nonConformances,[]);
  assert.deepEqual(entry.statuses,{a:'yes',c:'no'}); assert.equal(entry.facts.a,'0');
  assert.equal(entry.itemTexts.a,'Встроенный');
  assert.deepEqual(localStorage.writes,[key]); assert.match(alerts[0],/без автоматической оценки/);
  assert.equal(localStorage.getItem('tasks_registry_default'),'[{"id":"old"}]');
});

test('pending print is limited to explicit no, escapes user text, never evaluates numeric facts', () => {
  const source=page('checklists');
  const {ctx,nodes,localStorage}=harness(source,['getAllItems','printPending','createTasksFromPending']);
  nodes.set('status_a',{value:'yes'}); nodes.set('fact_a',{value:'1'});
  nodes.set('status_b',{value:'unknown'}); nodes.set('status_c',{value:'no'});
  vm.runInContext(`masterItems.c.text = '<script>alert(1)</script>';`,ctx);
  let output=''; ctx.escapeHtml = value=>String(value??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  ctx.window={open:()=>({document:{write: s => output=s,close:()=>{}},print:()=>{}})};
  ctx.printPending(); ctx.createTasksFromPending();
  assert.match(output,/&lt;script&gt;/); assert.doesNotMatch(output,/<script>/);
  assert.doesNotMatch(output,/Встроенный|Скрытый/); assert.deepEqual(localStorage.writes,[]);
  assert.match(source,/class="print-category-btn"[^>]*disabled/);
});

test('audit reports distinguish new unscored responses from legacy estimates', () => {
  const source=page('report-generator');
  const ctx={escapeHtml: value=>String(value??'').replace(/</g,'&lt;')}; vm.createContext(ctx);
  vm.runInContext(extract(source,'renderAuditReport'),ctx);
  const data={method:'manual-responses-v1',type:'Плановый',date:'2026-11-17T00:00:00Z',statuses:{a:'yes'},facts:{a:'0'},itemTexts:{a:'<img>'}};
  const report=ctx.renderAuditReport(data);
  assert.match(report,/Ручные ответы/); assert.match(report,/&lt;img>/); assert.doesNotMatch(report,/null%|уровень зрелости/i);
  const legacy=ctx.renderAuditReport({date:data.date,type:'Плановый',totalPercent:90,sectionScores:{},nonConformances:[]});
  assert.match(legacy,/Историческая оценка/); assert.match(legacy,/90%/);
  for (const name of ['dashboard','audit-registry']) {
    assert.match(page(name),/manual-responses-v1/); assert.match(page(name),/не проверено|непроверенная оценка/);
  }
  assert.doesNotMatch(page('dashboard'), /getLatestNonConformances\(\)\.forEach/);
});

test('paused checklist import preserves hidden answers and custom items', () => {
  const source=page('checklists'), key='checklist_current_form_default';
  const saved=JSON.stringify({b:{status:'yes',fact:''}});
  const {ctx,localStorage}=harness(source,['importData'],{[key]:saved});
  ctx.importData(JSON.stringify({customItems:{custom_1:{text:'Свое'}},currentFormState:{b:{status:'no'}}}));
  assert.equal(localStorage.getItem(key),saved);assert.deepEqual(localStorage.writes,[]);
});

test('inline application scripts parse', () => {
  for (const name of ['auditor','checklists','audit-registry','report-generator','dashboard']) {
    const scripts=[...page(name).matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(Boolean);
    assert.ok(scripts.length); for (const script of scripts) new vm.Script(script, {filename:name});
  }
});
