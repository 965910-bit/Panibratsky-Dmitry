'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
test('home and career expose both approved resume links securely',()=>{
 const urls=['https://surgut.hh.ru/resume/33d5f7abff115bad460039ed1f7166544f5263','https://surgut.zarplata.ru/resume/dc1875b3ff115ecddd0039ed1f6c487a655144'];
 for(const file of ['index.html','career.html']){
  const html=fs.readFileSync(file,'utf8');
  for(const url of urls){const tag=[...html.matchAll(/<a\b[^>]*>/g)].map(m=>m[0]).find(t=>t.includes(`href="${url}"`));assert.ok(tag,`${file} missing ${url}`);assert.match(tag,/target="_blank"/);assert.match(tag,/rel="noopener noreferrer"/);}
 }
});
