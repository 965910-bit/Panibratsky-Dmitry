'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const cp=require('node:child_process');
function extract(page,name) {
  const m=page.match(new RegExp(`^    function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n    \\}`, 'm'));
  assert.ok(m,name); return m[0];
}
const dashboard=fs.readFileSync('scm-platform/dashboard.html','utf8');
const escapeHtml=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
test('homepage inline CSS matches canonical source; analytics remains present and CSS precedes it',()=>{
  const html=fs.readFileSync('index.html','utf8'), css=fs.readFileSync('css/executive.css','utf8');
  const marker=html.match(/<!-- HOME_STYLES_START -->\n<style>\n([\s\S]*?)\n<\/style>\n<!-- HOME_STYLES_END -->/);
  assert.ok(marker);assert.equal(marker[1],css);assert.ok(!css.toLowerCase().includes('</style'));
  assert.doesNotMatch(html,/<link rel="stylesheet" href="css\/executive.css"/);
  assert.ok(html.indexOf('HOME_STYLES_START')<html.indexOf('googletagmanager.com/gtag/js'));
  assert.match(html,/googletagmanager\.com\/gtag\/js/);assert.match(html,/mc\.yandex\.ru\/metrika\/tag\.js/);
  const check=cp.spawnSync('python3',['scripts/sync_home_styles.py','--check'],{encoding:'utf8'});assert.equal(check.status,0,check.stderr);
});
test('paused shared imports preserve every legacy key and never parse payload',()=>{
  const source=fs.readFileSync('scm-platform/scm-common.js','utf8');
  const store=new Map([['scm_current_branch','default'],['scm_branches','[{"id":"default"}]'],['kpi_otd_default','{"result":50}']]);
  let writes=0;const localStorage={getItem:k=>store.get(k)??null,setItem:(k,v)=>{writes++;store.set(k,v)}};
  const window={dispatchEvent(){throw Error('unexpected dispatch')}};
  const ctx={window,localStorage,document:{addEventListener(){}},CustomEvent:class{}};vm.createContext(ctx);vm.runInContext(source,ctx);
  assert.equal(window.SCMData.importAllData('{"kpi_otd_default":"bad"}','default'),false);
  assert.throws(()=>window.BranchManager.importBranches([]),/приостановлен/);
  assert.equal(writes,0);assert.equal(store.get('kpi_otd_default'),'{"result":50}');assert.equal(store.get('scm_branches'),'[{"id":"default"}]');
  const branch=fs.readFileSync('scm-platform/branches.html','utf8');
  const ctx2={alert(){},FileReader:class{constructor(){throw Error('must not read')}}};vm.createContext(ctx2);vm.runInContext(extract(branch,'importBranches'),ctx2);ctx2.importBranches('{}');
  assert.match(branch,/id="importBranchesBtn" disabled/);
});
test('legacy budget strings are escaped; missing fields do not crash and zero is retained',()=>{
  const node={innerHTML:''};
  const ctx={document:{getElementById:()=>node},getBranchBudget:()=>Object.fromEntries(['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'].map(m=>[m,{opex:'<img src=x onerror=alert(1)>',payroll:0,transport:null}])),getBranchStaff:()=>[],currentBranchId:'default',Date,escapeHtml};
  vm.createContext(ctx);vm.runInContext(extract(dashboard,'renderBudgetStaff'),ctx);ctx.renderBudgetStaff();
  assert.doesNotMatch(node.innerHTML,/<img/);assert.match(node.innerHTML,/&lt;img/);assert.match(node.innerHTML,/введённый бюджет\): 0/);assert.match(node.innerHTML,/CAPEX: —/);
  const vals={productivity:0,pickErrors:0,otd:0,spaceUtil:0};ctx.getLastKPI=k=>vals[k];vm.runInContext(extract(dashboard,'renderWarehouseStats'),ctx);ctx.renderWarehouseStats();assert.equal((node.innerHTML.match(/<strong>0 /g)||[]).length,4);
});
test('invalid or non-finite legacy KPI history cannot produce a forecast or crash rendering',()=>{
  const node={innerHTML:''}; let history=[{value:1},{value:2}];
  const ctx={document:{getElementById:()=>node},getKPIHistory:()=>history};vm.createContext(ctx);
  vm.runInContext([extract(dashboard,'linearRegressionForecast'),extract(dashboard,'renderForecast')].join('\n'),ctx);
  assert.equal(ctx.linearRegressionForecast([{value:1},{value:2}]),3);ctx.renderForecast();assert.match(node.innerHTML,/2\.0 → 3\.0/);
  for (const invalid of [null,[],[{value:'<img>'},{value:'1'}],[{value:1},{value:NaN}],[{value:1e308},{value:1e308}],[null,{value:1}]]){
    history=invalid;assert.equal(ctx.linearRegressionForecast(invalid),null);ctx.renderForecast();assert.doesNotMatch(node.innerHTML,/<img/);assert.match(node.innerHTML,/недостаточно корректных данных/);
  }
});
