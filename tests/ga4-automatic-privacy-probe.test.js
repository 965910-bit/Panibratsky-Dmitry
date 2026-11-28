'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {marker,markerPresent}=require('../scripts/analytics_ga4_automatic_privacy_probe.cjs');
test('recognizes plain, encoded and post body synthetic markers only',()=>{
 assert(markerPresent('https://google.example/?q='+marker,''));
 assert(markerPresent('https://google.example/', 'dl=https%253A%252F%252Fexample.com%252F%253Fq%253D'+marker));
 assert.equal(markerPresent('https://example.com/?q=ordinary',''),false);
 assert.equal(markerPresent('https://example.com/?bad=%Q0',''),false);
});
