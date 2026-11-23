'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');
const code=fs.readFileSync('js/vizitka-contacts.js','utf8');
function setup(confirm=true){
 const els={};for(const id of ['contact-input','contact-select','email','contacts-status','contacts-load','contacts-clear','contact-use','contact-mark']) els[id]={value:'',textContent:'',children:[],addEventListener(t,f){this.click=f},replaceChildren(){this.children=[]},append(x){this.children.push(x)},focus(){this.focused=true}};
 vm.runInNewContext(code,{document:{getElementById:id=>els[id],createElement:()=>({value:'',textContent:''})},window:{confirm:()=>confirm},Set});return els;
}
test('list is session only, deduplicated, selection and manual marks never send',()=>{
 const x=setup();x['contact-input'].value='a@example.com\nB@example.com\na@example.com';x['contacts-load'].click();assert.equal(x['contact-select'].children.length,3);assert.match(x['contacts-status'].textContent,/2/);assert.equal(x['contact-input'].value,'');
 x['contact-select'].value='B@example.com';x['contact-use'].click();assert.equal(x.email.value,'B@example.com');x['contact-mark'].click();assert.match(x['contacts-status'].textContent,/Доставка не подтверждена/);assert.match(x['contact-select'].children[2].textContent,/отмечено вручную/);
 x['contacts-clear'].click();assert.equal(x['contact-select'].children.length,1);assert.equal(x.email.value,'');
});
test('invalid or oversized lists are rejected without replacing existing list',()=>{
 const x=setup();x['contact-input'].value='a@example.com';x['contacts-load'].click();x['contact-input'].value='x@example.com,hidden@example.com';x['contacts-load'].click();assert.equal(x['contact-select'].children.length,2);assert.match(x['contacts-status'].textContent,/не изменён/);
 x['contact-input'].value=Array(101).fill('a@example.com').join('\n');x['contacts-load'].click();assert.equal(x['contact-select'].children.length,2);
});
test('clearing and replacement require confirmation',()=>{
 const x=setup(false);x['contact-input'].value='a@example.com';x['contacts-load'].click();x['contact-input'].value='b@example.com';x['contacts-load'].click();assert.equal(x['contact-select'].children[1].value,'a@example.com');x['contacts-clear'].click();assert.equal(x['contact-select'].children.length,2);
});
test('the page clearly states limitations and neither script stores or sends contacts',()=>{
 const html=fs.readFileSync('vizitka.html','utf8');assert.match(html,/не защищённая админ-панель/);assert.match(html,/Автоматическая рассылка пока не подключена/);assert.match(html,/connect-src 'none'/);
 assert.doesNotMatch(code,/localStorage|sessionStorage|fetch\s*\(|XMLHttpRequest|innerHTML/);
});
