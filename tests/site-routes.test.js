'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const read=p=>fs.readFileSync(p,'utf8');
test('homepage gives employers and readers direct access to existing public routes',()=>{
 const html=read('index.html');
 assert.match(html,/Для работодателя/);
 assert.match(html,/Сургут и ХМАО в приоритете/);
 const resources=html.match(/<section[^>]+id="resources"[\s\S]*?<\/section>\s*<section class="assistant-section"/)[0];
 for (const page of ['calculators.html','projects.html','scm-knowledge.html','scm-navigator.html','scm-practical-guides.html','scm-diagnostic.html','scm-academy.html','scm-internal-academy.html']) {
   assert.ok(resources.includes(`href="${page}"`),page);
   assert.ok(fs.existsSync(page),page);
   const sitemap=read('sitemap.xml');assert.ok(sitemap.includes(`https://scm-news.ru/${page}`),page);
 }
});
test('career path includes federal employers and verified project context',()=>{
 const career=read('career.html');
 assert.match(career,/головными офисами из других регионов России/);
 assert.match(career,/переезд возможен при предоставлении релокационного пакета/);
 assert.match(career,/href="projects\.html"/);
 const projects=read('projects.html');
 assert.match(projects,/href="career\.html"/);
 assert.match(projects,/сумма дефекта по данным резюме/);
 assert.doesNotMatch(projects,/<h4>Управленческий фокус/);
 assert.match(projects,/\.project-achievements h3/);
});
test('all added destination pages use the existing consent and event handlers',()=>{
 for(const page of ['scm-knowledge.html','scm-navigator.html','scm-practical-guides.html','scm-diagnostic.html','scm-academy.html','scm-internal-academy.html','projects.html']){
  const html=read(page);
  assert.equal((html.match(/src="js\/analytics-consent\.js"/g)||[]).length,1,page);
  assert.equal((html.match(/src="js\/visitor-events\.js"/g)||[]).length,1,page);
 }
});
