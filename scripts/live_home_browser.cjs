'use strict';
// Read-only synthetic smoke of the published homepage. Analytics and all other
// third parties are blocked to avoid measurement pollution. Not a PSI run.
const { chromium } = require('playwright-core');
const host = 'https://scm-news.ru/';
const path = process.env.CHROME_PATH;
if (!path) throw Error('CHROME_PATH is required');
const extra = JSON.parse(process.env.BROWSER_ARGS || '[]');

async function probe(width, dpr) {
  const browser = await chromium.launch({ executablePath: path, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage', ...extra] });
  try {
    const page = await browser.newPage({viewport:{width, height:823}, deviceScaleFactor:dpr});
    await page.addInitScript(() => {
      window.__shifts = [];
      new PerformanceObserver(list => list.getEntries().forEach(entry => {
        if (!entry.hadRecentInput) window.__shifts.push(entry.value);
      })).observe({type:'layout-shift', buffered:true});
    });
    await page.route('**/*', async route => {
      const url = route.request().url();
      if (!url.startsWith(host)) return route.abort();
      if (url.endsWith('/js/executive.js')) await new Promise(resolve => setTimeout(resolve, 1500));
      return route.continue();
    });
    const response = await page.goto(host, {waitUntil:'load', timeout:30000});
    if (!response || response.status() !== 200) throw Error('Homepage did not return 200');
    await page.waitForTimeout(300);
    const data = await page.evaluate(() => ({
      cls: window.__shifts.reduce((sum, x) => sum + x, 0),
      header: Math.round(document.querySelector('.site-header').getBoundingClientRect().height),
      image: new URL(document.querySelector('.portrait-frame img').currentSrc).pathname,
    }));
    if (data.cls >= 0.01) throw Error('Unexpected layout shift: ' + data.cls.toFixed(4));
    if (data.header !== (width <= 820 ? 68 : 83)) throw Error('Unexpected header height');
    if (!/^\/images\/profile-hero(?:-(?:480|640))?\.webp$/.test(data.image)) throw Error('Unexpected portrait');
    if (width <= 820) {
      const control = page.getByRole('checkbox', {name:'Показать меню'});
      await control.focus();
      await page.keyboard.press('Space');
      if (!await page.locator('#site-nav').isVisible()) throw Error('Menu did not open');
      await page.keyboard.press('Escape');
      if (await page.locator('#site-nav').isVisible()) throw Error('Menu did not close');
    }
    console.log(`::notice title=Production browser ${width}px::CLS=${data.cls.toFixed(4)}, header=${data.header}px, portrait=${data.image}; third parties blocked; JS delayed 1.5s`);
  } finally { await browser.close(); }
}
(async () => { await probe(412, 1.75); await probe(1350, 1); })().catch(() => {
  // Do not dump browser console, third-party URLs or request details into logs.
  console.error('::error title=Production browser smoke::Homepage test failed. Inspect published page and retry; third parties were blocked.');
  process.exitCode = 1;
});
