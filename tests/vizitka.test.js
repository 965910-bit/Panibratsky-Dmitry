'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const script=fs.readFileSync('js/vizitka.js','utf8');
function setup(opts={}){
 const elements={};for(const id of ['message','subject','email','status','copy','reset','email-button','short-template']) elements[id]={value:'',textContent:'',validity:{valid:true},addEventListener(_type,fn){this.click=fn},focus(){this.focused=true},select(){this.selected=true}};
 elements.message.value='Визитка и https://scm-news.ru/';elements.subject.value='Тема';let copied=[];
 const navigator={clipboard:opts.noClipboard?undefined:{writeText:async s=>{if(opts.failCopy)throw Error();copied.push(s)}}};
 const window={location:{href:''},confirm:()=>opts.confirm??true};
 vm.runInNewContext(script,{document:{getElementById:id=>elements[id]},window,navigator,encodeURIComponent});
 return {elements,window,copied};
}
test('copy sends only current text to clipboard, or selects it if unavailable',async()=>{
 const a=setup();a.elements.message.value='Здравствуйте!';await a.elements.copy.click();assert.deepEqual(a.copied,['Здравствуйте!']);assert.match(a.elements.status.textContent,/скопирован/);
 const b=setup({noClipboard:true});await b.elements.copy.click();assert.equal(b.elements.message.selected,true);assert.match(b.elements.status.textContent,/вручную/);
});
test('one safe recipient creates editable mail draft, never sends it directly',()=>{
 const x=setup();x.elements.email.value='name+tag@example.com';x.elements['email-button'].click();
 const mail=x.window.location.href;assert.match(mail,/^mailto:name%2Btag@example\.com\?subject=/);assert.equal(new URLSearchParams(mail.split('?')[1]).get('body'),x.elements.message.value);
 assert.equal(new URLSearchParams(mail.split('?')[1]).get('subject'),x.elements.subject.value);
 for(const bad of ['x@example.com,y@example.com','a@example.com\nBcc:secret@example.com','', 'a@example.com?bcc=x@example.com']) {x.window.location.href='';x.elements.email.value=bad;x.elements['email-button'].click();assert.equal(x.window.location.href,'');}
 x.elements.email.value='name@example.com';x.elements.subject.value='x\nBcc:bad@example.com';x.window.location.href='';x.elements['email-button'].click();assert.equal(x.window.location.href,'');
});
test('reset requires confirmation before losing edits',()=>{
 const x=setup({confirm:false});x.elements.message.value='изменено';x.elements.reset.click();assert.equal(x.elements.message.value,'изменено');
 const y=setup();y.elements.message.value='изменено';y.elements.reset.click();assert.match(y.elements.message.value,/Визитка/);
});
test('page has no analytics, storage or remote requests and includes actual links',()=>{
 const html=fs.readFileSync('vizitka.html','utf8');
 for(const url of ['https://scm-news.ru/','https://scm-news.ru/documents/gerasimov-presentation.pdf','https://surgut.hh.ru/resume/33d5f7abff115bad460039ed1f7166544f5263','https://surgut.zarplata.ru/resume/dc1875b3ff115ecddd0039ed1f6c487a655144'])assert.ok(html.includes(url));
 assert.match(html,/connect-src 'none'/);assert.doesNotMatch(html,/googletagmanager|mc\.yandex|<form/i);assert.doesNotMatch(script,/localStorage|sessionStorage|fetch\s*\(|XMLHttpRequest/);
 assert.doesNotMatch(fs.readFileSync('index.html','utf8'),/href="vizitka.html"/);
});

test('short template is editable, retains key links, and protects edits',()=>{
 const x=setup();x.elements['short-template'].click();
 for(const value of ['Академии', 'готовящейся к изданию', 'https://scm-news.ru/', 'gerasimov-presentation.pdf', 'surgut.hh.ru/resume/', 'surgut.zarplata.ru/resume/']) assert.ok(x.elements.message.value.includes(value));
 const y=setup({confirm:false});y.elements.message.value='Мои правки';y.elements['short-template'].click();assert.equal(y.elements.message.value,'Мои правки');
});
test('photo and PDF are available for manual attachment',()=>{
 const html=fs.readFileSync('vizitka.html','utf8');
 assert.match(html,/img-src 'self'/);assert.match(html,/images\/profile-hero\.webp/);assert.match(html,/прикрепите нужный файл/);
 assert.ok(fs.existsSync('images/profile-hero.webp'));assert.ok(fs.existsSync('documents/gerasimov-presentation.pdf'));
});
