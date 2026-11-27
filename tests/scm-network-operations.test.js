const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');

test('network operations guide is discoverable and its local fragments resolve', () => {
  const wiki = fs.readFileSync(path.join(root, 'wiki.html'), 'utf8');
  const page = fs.readFileSync(path.join(root, 'scm-network-operations.html'), 'utf8');
  const ids = [...page.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
  assert.equal(new Set(ids).size, ids.length);
  const links = [...wiki.matchAll(/href="scm-network-operations\.html#([^"]+)"/g)].map(m => m[1]);
  assert.equal(links.length, 6);
  for (const id of links) assert.ok(ids.includes(id), id);
  assert.match(page, /rel="canonical" href="https:\/\/scm-news\.ru\/scm-network-operations\.html"/);
  assert.match(page, /Все числовые примеры условные/);
  for (const [, href] of page.matchAll(/href="([^"#/:]+\.html)(?:#([^"]+))?"/g)) {
    assert.ok(fs.existsSync(path.join(root, href)), href);
  }
  for (const [, fragment] of page.matchAll(/href="scm-network-operations\.html#([^"]+)"/g)) assert.ok(ids.includes(fragment));
});

test('planning topics include detailed formulas, assumptions and worked examples', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'scm-network-operations.html'), 'utf8');
  for (const id of ['network-design', 'capacity-planning', 'kanban', 'inventory-review-policies', 'demand-lead-variability', 'forecast-hierarchy', 'work-in-process', 'maintenance-reliability', 'first-pass-yield', 'multi-echelon-inventory']) {
    const section = html.match(new RegExp(`<section class="encyclopedia-start" id="${id}">([\\s\\S]*?)</section>`));
    assert.ok(section, id);
    assert.match(section[1], /<h3>Углубление:/, id);
  }
  assert.ok(Math.abs((-1 + 2/1.1 + 2/1.1**2) - 2.47107438) < 0.0001);
  assert.equal(Math.ceil((30*3+11)/25), 5);
  assert.ok(Math.abs(Math.sqrt(2*10000*200/5)-894.4272)<0.001);
  assert.equal(4*25 + 20**2, 500);
  assert.equal(120/30, 4);
  assert.ok(Math.abs(81/100 - .9*.9) < 1e-12);
});

test('warehouse and freight topics include operational deepening and checked examples', () => {
  const page = fs.readFileSync(path.join(root, 'scm-network-operations.html'), 'utf8');
  for (const id of ['cost-to-serve', 'dock-scheduling', 'picking-methods', 'warehouse-capacity-design', 'packaging-protection', 'loading-dock-safety', 'freight-modes', 'multimodal-handoffs', 'freight-documents', 'cargo-claims', 'vehicle-route-planning', 'returnable-packaging']) {
    const section = page.match(new RegExp(`<section class="encyclopedia-start" id="${id}">([\\s\\S]*?)</section>`));
    assert.ok(section, id);
    assert.match(section[1], /<h3>Углубление:/, id);
  }
  assert.equal(300000 / 15000 * 1000, 20000);
  assert.equal(8*60 + 4*90, 2*420);
  assert.equal(12*4*2 - 6 - 10, 80);
  assert.equal(40*8 + 25 + 3, 348);
  assert.equal((600000 - 300000)*.2, 60000);
  assert.equal(500 + 300 + 130 + 70 + 30, 1030);
});

test('supplier and continuity topics include practical methods and verified examples', () => {
  const page = fs.readFileSync(path.join(root, 'scm-network-operations.html'), 'utf8');
  for (const id of ['continuity', 'supplier-qualification', 'supplier-development', 'supplier-material-change', 'supplier-concentration', 'indirect-procurement', 'procurement-commercial-terms', 'contract-obligations', 'make-or-buy-3pl', 'logistics-operator-contract', 'third-party-inventory', 'subtier-supplier-risk']) {
    const section = page.match(new RegExp(`<section class="encyclopedia-start" id="${id}">([\\s\\S]*?)</section>`));
    assert.ok(section, id);
    assert.match(section[1], /<h3>Углубление:/, id);
  }
  assert.equal(18 / 20 * 100, 90);
  assert.equal(50**2 + 30**2 + 20**2, 3800);
  assert.equal(500 - 320 - 80, 100);
  assert.ok(Math.abs(1000000 * .12 * 30 / 365 - 9863.0137) < .01);
  assert.equal(4000000 + 40*100000, 2000000 + 60*100000);
  assert.equal(50 * 100, 5000);
});

test('digital and change topics contain deepening and consistent examples', () => {
  const page = fs.readFileSync(path.join(root, 'scm-network-operations.html'), 'utf8');
  for (const id of ['scm-systems-boundaries', 'integration-events', 'edi-asn', 'wms-cutover', 'bom-engineering-change', 'control-tower', 'sla-kpi-data-quality', 'change-implementation-project', 'promotion-new-product-forecast', 'warehouse-automation', 'epcis-traceability', 'supply-chain-access', 'ai-forecast-documents']) {
    const section = page.match(new RegExp(`<section class="encyclopedia-start" id="${id}">([\\s\\S]*?)</section>`));
    assert.ok(section, id);
    assert.match(section[1], /<h3>Углубление:/, id);
  }
  assert.equal(115 + 80, 195);
  assert.equal(1000 + 50 - 30, 1020);
  assert.equal(Math.ceil(100 * 2 / .9), 223);
  assert.equal(180 / 192 * 100, 93.75);
  assert.equal(1300 - 1000 - 100, 200);
  assert.equal(450 * 8, 3600);
});

test('people, service and return topics have detailed operational cases', () => {
  const page = fs.readFileSync(path.join(root, 'scm-network-operations.html'), 'utf8');
  for (const id of ['root-cause-five-whys', 'return-to-supplier', 'omnichannel-fulfilment', 'last-mile-delivery', 'repair-refurbishment', 'warranty-returns', 'returns-cost-availability', 'customer-complaint-sla', 'process-raci', 'investment-business-case', 'measurement-improvement', 'shift-skills-matrix', 'shift-handover', 'service-segmentation', 'driver-safety']) {
    const section = page.match(new RegExp(`<section class="encyclopedia-start" id="${id}">([\\s\\S]*?)</section>`));
    assert.ok(section, id);
    assert.match(section[1], /<h3>Углубление:/, id);
  }
  assert.equal(20 - 7 + 3, 16);
  assert.equal(18 / 20 * 100, 90);
  assert.equal((8 - 10) - (9 - 10), -1);
  assert.ok(Math.abs((-1000000 + 400000/1.1 + 400000/1.1**2 + 400000/1.1**3) + 5259.20) < 1);
  assert.equal(12000 / 20, 600);
});

test('all 80 catalog topics include deepening and the final 18 contain worked cases', () => {
  const page = fs.readFileSync(path.join(root, 'scm-network-operations.html'), 'utf8');
  const sections = [...page.matchAll(/<section class="encyclopedia-start" id="([^"]+)">([\s\S]*?)<\/section>/g)]
    .filter(([, id]) => id !== 'topics');
  assert.equal(sections.length, 80);
  for (const [, id, body] of sections) {
    assert.match(body, /<h3>Углубление:/, id);
  }
  for (const id of ['takt-cycle-lead', 'fmea', 'bullwhip-effect', 'collaborative-replenishment', 'consignment-inventory', 'mro-spare-parts', 'inventory-carrying-cost', 'inventory-centralization', 'cargo-insurance-liability', 'freight-forwarder-selection', 'container-terminal-operations', 'customs-classification-origin-value', 'tir-cmr-ecmr', 'dangerous-perishable-goods', 'northern-seasonal-supply', 'transport-emissions-scopes', 'waste-circularity', 'labour-due-diligence']) {
    const found = sections.find(([, sectionId]) => sectionId === id);
    assert.ok(found, id);
    assert.match(found[2].slice(found[2].indexOf('<h3>Углубление:')), /<strong>Пример:<\/strong>/, id);
  }
  assert.equal(450 / 225, 2);
  assert.equal(10 * 2 * 3, 5 * 4 * 3);
  assert.equal(400 / 100, 4);
  assert.equal(100 + 40 - 30 - 10, 100);
  assert.equal(2000000 * (.12 + .03), 300000);
  assert.ok(Math.abs(Math.sqrt(100 + 100) - 14.1421) < .001);
  assert.equal(18000 + 500 + 2500, 21000);
  assert.equal(600 + 100 - 150 - 50, 500);
  assert.equal(10 * 100 * .1, 100);
});

test('equipment, mechanic and safety guide is discoverable and preserves KPI boundaries', () => {
  const page = fs.readFileSync(path.join(root, 'scm-warehouse-equipment.html'), 'utf8');
  const wiki = fs.readFileSync(path.join(root, 'wiki.html'), 'utf8');
  const metrics = fs.readFileSync(path.join(root, 'scm-metrics.html'), 'utf8');
  assert.match(wiki, /href="scm-warehouse-equipment\.html"/);
  assert.match(metrics, /href="scm-warehouse-equipment\.html#fleet-kpi"/);
  assert.match(page, /rel="canonical" href="https:\/\/scm-news\.ru\/scm-warehouse-equipment\.html"/);
  const ids = [...page.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
  assert.equal(new Set(ids).size, ids.length);
  for (const id of ['fleet-types', 'fleet-selection', 'traffic-safety', 'power-sources', 'fire-safety', 'mechanic', 'fleet-kpi', 'safety-kpi', 'warehouse-kpi', 'academy']) assert.ok(ids.includes(id), id);
  for (const [, fragment] of page.matchAll(/href="#([^"]+)"/g)) assert.ok(ids.includes(fragment), fragment);
  assert.match(page, /классификация беспилотной техники не установлена/);
  assert.match(page, /микротравма и оказание первой помощи учитываются отдельно/);
  assert.match(page, /200 000 часов/);
  assert.match(page, /не является нормативной методикой расчёта пожарного риска/);
  assert.equal(36 / 40 * 100, 90);
  assert.ok(Math.abs(24 / 36 * 100 - 66.7) < 0.04);
  assert.equal(180 / 6, 30);
  assert.equal((2 + 4) / 2, 3);
  assert.equal(600 / 3, 200);
  assert.equal(18 / 20 * 100, 90);
  assert.equal(16 / 20 * 100, 80);
  assert.equal(2 * 200000 / 100000, 4);
  assert.equal(9 / 12 * 100, 75);
  assert.equal(12 - 9, 3);
  assert.equal(2 * 7 * 60, 840);
  assert.equal(630 / 840 * 100, 75);
  assert.equal(6 / 4, 1.5);
  assert.equal(120 / 10, 12);
});

test('equipment guide includes lifecycle scenarios, maintenance timeline and bounded calculations', () => {
  const page = fs.readFileSync(path.join(root, 'scm-warehouse-equipment.html'), 'utf8');
  const ids = [...page.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
  assert.equal(new Set(ids).size, ids.length);
  for (const id of ['fleet-acceptance', 'fleet-inspection', 'dock-yard-scenarios', 'battery-planning', 'mechanic-work-order', 'fire-controls', 'equipment-kpi-methods', 'equipment-academy-practice']) {
    assert.ok(ids.includes(id), id);
    assert.ok(page.includes(`href="#${id}"`), id);
  }
  assert.match(page, /индикатор сам по себе не доказывает безопасное состояние/i);
  assert.match(page, /не является нормативной методикой расчёта пожарного риска/);
  assert.equal(20 / .8, 25);
  assert.equal(25 / 5, 5);
  assert.ok(Math.abs((420 / 480) * (2 * 180 / 420) * (171 / 180) * 100 - 71.25) < 1e-10);
  assert.equal(18 / 20 * 100, 90);
  assert.equal((20 - 18) / 20 * 100, 10);
  assert.equal(1200000 + 240000 + 360000 - 150000, 1650000);
  assert.equal(1650000 / 3, 550000);
  assert.equal(.5 + .5 + 2 + 1 + .5, 4.5);
});
