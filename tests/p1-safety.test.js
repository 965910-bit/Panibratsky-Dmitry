'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
function func(page,name) {
  const match=page.match(new RegExp(`        function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?\\n        \\}`));
  assert.ok(match, name); return match[0];
}
for (const name of ['admin.html','js/analytics.js']) {
  test(`${name}: maps tolerate missing clustering, invalid coordinates and missing Leaflet`,()=>{
    const page=fs.readFileSync(name,'utf8');
    const table={innerHTML:''},status={textContent:''},markers=[];
    let groups=0, removes=0, clears=0;
    const ctx={
      document:{querySelector:()=>table,getElementById:()=>status},
      getData:()=>[
        {city:'Zero',region:'R',lat:0,lon:0},
        {city:'Late',region:'R'},
        {city:'Late',region:'R',lat:55,lon:37},
        {city:'Invalid',region:'<script>',lat:'55',lon:37},
        {city:'Overflow',region:'R',lat:91,lon:37},
        {city:'NaN',region:'R',lat:NaN,lon:37}, null
      ],
      L:{map:()=>({setView(){return this},addLayer(){},remove(){removes++}}),tileLayer:()=>({addTo(){}}),
        layerGroup:()=>{groups++;return {addLayer(){},clearLayers(){clears++}}},
        marker:coords=>{markers.push(Array.from(coords));return {bindPopup(){}}}},
      russiaMap:undefined,markerCluster:undefined
    };
    vm.createContext(ctx);vm.runInContext([func(page,'escapeHtml'),func(page,'renderRussiaMap')].join('\n'),ctx);
    ctx.renderRussiaMap();assert.equal(groups,1);assert.deepEqual(markers.sort((a,b)=>a[0]-b[0]),[[0,0],[55,37]]);
    assert.match(table.innerHTML,/0\.00, 0\.00/);assert.match(table.innerHTML,/55\.00, 37\.00/);
    assert.doesNotMatch(table.innerHTML,/<script>/);assert.match(table.innerHTML,/&lt;script&gt;/);
    ctx.renderRussiaMap();assert.equal(groups,2);assert.equal(removes,1);assert.equal(clears,1);
    ctx.L=undefined;ctx.renderRussiaMap();assert.match(status.textContent,/Карта недоступна/);assert.match(table.innerHTML,/Invalid/);
  });
}
test('local Leaflet distribution and license match the exact npm dependency',()=>{
  const pkg=JSON.parse(fs.readFileSync('package.json','utf8'));assert.equal(pkg.dependencies.leaflet,'1.9.4');
  const base='js/vendor/leaflet-1.9.4', npm='node_modules/leaflet';
  for(const file of ['leaflet.js','leaflet.js.map','leaflet.css','images/layers.png','images/layers-2x.png','images/marker-icon.png','images/marker-icon-2x.png','images/marker-shadow.png']) {
    assert.deepEqual(fs.readFileSync(path.join(base,file)),fs.readFileSync(path.join(npm,'dist',file)),file);
  }
  assert.deepEqual(fs.readFileSync(path.join(base,'LICENSE')),fs.readFileSync(path.join(npm,'LICENSE')));
  const html=fs.readFileSync('admin.html','utf8');
  assert.match(html,/js\/vendor\/leaflet-1\.9\.4\/leaflet\.js/);
  assert.match(html,/js\/vendor\/leaflet-1\.9\.4\/leaflet\.css/);
  assert.doesNotMatch(html,/unpkg\.com\/leaflet/);
});
