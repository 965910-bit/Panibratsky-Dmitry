'use strict';
// Real-browser regression, not a Lighthouse or field measurement.
// CHROME_PATH points to an installed Chrome/Chromium. BROWSER_ARGS optionally
// supplies a JSON array of extra flags (e.g. for serverless Chromium).
const { test } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright-core');

const root = path.resolve(__dirname, '..');
const chrome = process.env.CHROME_PATH;
if (!chrome) throw new Error('Set CHROME_PATH to an installed Chrome/Chromium');
const args = ['--no-sandbox', '--disable-dev-shm-usage', ...JSON.parse(process.env.BROWSER_ARGS || '[]')];

async function scenario({ width, dpr, javascriptEnabled = true }) {
  const hits = [];
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    const name = url.pathname === '/' ? '/index.html' : url.pathname;
    const allowed = ['/index.html', '/js/executive.js', '/images/profile-hero.webp', '/images/profile-hero-480.webp', '/images/profile-hero-640.webp'];
    if (!allowed.includes(name)) { res.writeHead(404); res.end(); return; }
    hits.push(name);
    const send = () => { res.setHeader('Content-Type', name.endsWith('.html') ? 'text/html; charset=utf-8' : name.endsWith('.js') ? 'text/javascript' : 'image/webp'); res.end(fs.readFileSync(path.join(root, name))); };
    // Paint the initial header before the deferred JS becomes available.
    if (name === '/js/executive.js') setTimeout(send, 1300); else send();
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  let browser;
  try {
    browser = await chromium.launch({ executablePath: chrome, headless: true, args });
    const context = await browser.newContext({ viewport: { width, height: 823 }, deviceScaleFactor: dpr, javascriptEnabled });
    const page = await context.newPage();
    await page.route('**/*', route => route.request().url().startsWith(base + '/') ? route.continue() : route.abort());
    if (javascriptEnabled) await page.addInitScript(() => {
      window.__layoutShifts = [];
      new PerformanceObserver(list => list.getEntries().forEach(entry => {
        if (!entry.hadRecentInput) window.__layoutShifts.push(entry.value);
      })).observe({ type: 'layout-shift', buffered: true });
    });
    await page.goto(base + '/', { waitUntil: 'load' });
    await page.waitForTimeout(250);
    const nav = page.locator('#site-nav');
    const menu = page.getByRole('checkbox', { name: 'Показать меню' });
    assert.equal(await page.locator('.site-header').evaluate(el => Math.round(el.getBoundingClientRect().height)), width <= 820 ? 68 : 83);
    assert.equal(await nav.isVisible(), width > 820);
    const heroKnowledge = page.locator('.hero-knowledge-link');
    assert.equal(await heroKnowledge.getAttribute('href'), 'wiki.html');
    assert.equal(await heroKnowledge.isVisible(), true);
    const heroBox = await heroKnowledge.boundingBox();
    assert.ok(heroBox.y + heroBox.height <= 823, `Knowledge link should be visible in the first viewport: ${JSON.stringify(heroBox)}`);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.equal(await page.locator('.resource-directory').evaluate(el => el.open), false);
    assert.equal(await page.locator('.resource-card-knowledge').getAttribute('href'), 'wiki.html');
    if (width > 820) {
      assert.equal(await nav.getByRole('link', {name: 'База знаний'}).isVisible(), true);
      const brandBox = await page.locator('.site-header .brand').boundingBox();
      const navBox = await nav.boundingBox();
      const themeBox = await page.locator('.theme-toggle').boundingBox();
      assert.ok(brandBox.x + brandBox.width <= navBox.x && navBox.x + navBox.width <= themeBox.x, 'Desktop navigation must not overlap brand or theme control');
    }

    if (javascriptEnabled) {
      const shifts = await page.evaluate(() => window.__layoutShifts);
      const cls = shifts.reduce((sum, value) => sum + value, 0);
      assert.ok(cls < 0.01, `Unexpected layout shift: ${cls}`);
    }
    const src = await page.locator('.portrait-frame img').evaluate(img => img.currentSrc);
    const expectedImage = width > 820 ? '/images/profile-hero-480.webp' : '/images/profile-hero-640.webp';
    assert.ok(src.endsWith(expectedImage), `Unexpected image: ${src}`);
    assert.deepEqual(hits.filter(hit => hit.startsWith('/images/profile-hero')), [expectedImage], 'Only the chosen portrait should be requested');
    if (width <= 820) {
      const toggleBox = await page.locator('.menu-toggle').boundingBox();
      assert.ok(toggleBox.width >= 44 && toggleBox.height >= 44, 'Menu target must be at least 44x44 CSS pixels');
      // Keyboard operation and focus outline work even without JavaScript.
      await menu.focus();
      assert.ok(await page.locator('.menu-check:focus-visible + .menu-toggle').count());
      await page.keyboard.press('Space');
      assert.equal(await menu.isChecked(), true);
      assert.equal(await nav.isVisible(), true);
      assert.equal(await nav.getByRole('link', {name: 'База знаний'}).getAttribute('href'), 'wiki.html');
      assert.equal(await page.locator('.hero').evaluate(el => Math.round(el.getBoundingClientRect().top)), 68);
      if (javascriptEnabled) {
        await page.keyboard.press('Escape');
        assert.equal(await menu.isChecked(), false);
        assert.equal(await nav.isVisible(), false);
        assert.equal(await menu.evaluate(el => el === document.activeElement), true);
        await page.keyboard.press('Space');
        await nav.locator('a[href="#cases"]').click();
        assert.equal(await menu.isChecked(), false, 'Navigating closes the menu when JavaScript is available');
        assert.equal(await nav.isVisible(), false);
      } else {
        await page.keyboard.press('Space');
        assert.equal(await menu.isChecked(), false);
        assert.equal(await nav.isVisible(), false);
      }
    }
    if (javascriptEnabled) {
      // Target the specific regressions from the supplied Lighthouse report,
      // plus the label/ARIA semantics of the replacement control.
      await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') });
      for (const mode of ['dark', 'light']) {
        if (mode === 'light') await page.locator('.theme-toggle').click();
        const violations = await page.evaluate(async () => (await window.axe.run(document, { runOnly: ['color-contrast', 'label', 'aria-allowed-attr'] })).violations.map(item => ({ id: item.id, targets: item.nodes.map(node => node.target) })));
        assert.deepEqual(violations, [], `${mode} accessibility violations: ${JSON.stringify(violations)}`);
      }
    }
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}

test('mobile: delayed JavaScript cannot shift header; keyboard menu works', async () => scenario({ width: 412, dpr: 1.75 }));
test('mobile: menu stays usable without JavaScript', async () => scenario({ width: 412, dpr: 1.75, javascriptEnabled: false }));
test('desktop: layout and responsive image stay stable', async () => scenario({ width: 1350, dpr: 1 }));

test('tablet desktop navigation does not overlap', async () => scenario({ width: 900, dpr: 1 }));
