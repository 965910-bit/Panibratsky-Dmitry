'use strict';
// Keep local and CI Node checks aligned; browser and legacy calculators are
// intentionally separate because they require a browser or a direct runner.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');

test('CI runs the shared Node test suite and all test files are covered', () => {
  const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
  const workflow = fs.readFileSync('.github/workflows/site-tests.yml', 'utf8');
  const suite = pkg.scripts['test:node'];
  assert.match(suite, /^node --test /);
  assert.match(pkg.scripts.test, /(?:^| && )npm run test:node(?: && |$)/);
  assert.match(workflow, /^\s*- run: npm run test:node\s*$/m);
  assert.match(workflow, /npm run test:browser/);
  assert.match(pkg.scripts['test:browser'], /tests\/homepage-browser\.test\.js/);
  assert.match(pkg.scripts['test:browser'], /tests\/inventory-tools-browser\.test\.js/);
  assert.match(pkg.scripts['test:browser'], /tests\/analytics-browser\.test\.js/);
  assert.match(pkg.scripts['test:browser'], /tests\/responsive-portraits-browser\.test\.js/);
  assert.match(workflow, /node tests\/calculators\.test\.js/);
  for (const file of fs.readdirSync('tests').filter(name => /\.test\.(js|mjs)$/.test(name))) {
    if (['homepage-browser.test.js', 'inventory-tools-browser.test.js', 'analytics-browser.test.js', 'responsive-portraits-browser.test.js', 'calculators.test.js'].includes(file)) continue;
    assert(suite.split(/\s+/).includes(`tests/${file}`), `${file} is missing from test:node`);
  }
});
