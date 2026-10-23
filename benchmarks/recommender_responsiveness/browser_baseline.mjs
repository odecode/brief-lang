// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// Test orchestration only. The served application and DB client remain Briev.
import fs from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const [url, username, password, output, samplesText = '200'] = process.argv.slice(2);
if (!url || !username || !password || !output) throw Error('url username password output [samples] required');
const samples = Number(samplesText);
if (!Number.isInteger(samples) || samples < 1) throw Error('samples must be positive');
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage();
const errors = [];
const protocol = [];
const cdp = await page.context().newCDPSession(page);
await cdp.send('Network.enable');
cdp.on('Network.requestWillBeSent', event => protocol.push({
  stage: 'request', method: event.request.method,
  path: new URL(event.request.url).pathname, timestamp: event.timestamp,
  id: event.requestId, type: event.type,
}));
cdp.on('Network.responseReceived', event => protocol.push({
  stage: 'response', status: event.response.status, timestamp: event.timestamp,
  id: event.requestId, type: event.type,
}));
page.on('pageerror', error => errors.push(String(error)));
await page.addInitScript(() => {
  const records = [];
  window.baseline = { records, operation: '', sequence: 0,
    prefix: 'browser_' + crypto.randomUUID().replaceAll('-', '') };
  const record = (stage, detail = {}) => records.push({
    operation: window.baseline.operation, stage, ms: performance.now(), ...detail,
  });
  document.addEventListener('click', event => {
    if (event.target.id !== 'save-rating') return;
    window.baseline.operation = `${window.baseline.prefix}_${++window.baseline.sequence}`;
    record('click', { purpose: window.baseline.purpose });
    requestAnimationFrame(() => requestAnimationFrame(() => record('paint_opportunity', {
      notice: document.querySelector('#notice').textContent,
      ratings: document.querySelector('#ratings').textContent,
      rating_count: Number(document.querySelector('#rating-count').textContent),
      recommendations: document.querySelector('#recommendations').textContent,
      recommendations_visible: getComputedStyle(document.querySelector('#recommendations')).display !== 'none',
    })));
  }, true);
  const open = XMLHttpRequest.prototype.open;
  const send = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(method, address, ...rest) {
    this.baselinePath = new URL(address, location.href).pathname;
    this.baselineMethod = method;
    return open.call(this, method, address, ...rest);
  };
  XMLHttpRequest.prototype.send = function(body) {
    if (this.baselinePath === '/rating' && window.baseline.operation) {
      body = JSON.stringify({ ...JSON.parse(body), trace_id: window.baseline.operation });
    }
    record('http_start', { path: this.baselinePath, method: this.baselineMethod });
    try {
      return send.call(this, body);
    } finally {
      record('http_end', { path: this.baselinePath, status: this.status });
    }
  };
  const NativeWebSocket = window.WebSocket;
  window.WebSocket = class extends NativeWebSocket {
    constructor(...args) {
      super(...args);
      this.addEventListener('message', event => {
        const result = JSON.parse(event.data);
        record('live_receive', { cold_start: result.cold_start,
          recommendations: result.recommendations });
      });
    }
  };
  new PerformanceObserver(list => {
    for (const entry of list.getEntries()) record('long_task', {
      start: entry.startTime, duration: entry.duration,
    });
  }).observe({ type: 'longtask', buffered: true });
  document.addEventListener('DOMContentLoaded', () => {
    const observer = new MutationObserver(mutations => {
      for (const id of ['notice', 'ratings', 'recommendations']) {
        const target = document.getElementById(id);
        if (mutations.some(change => target?.contains(change.target))) record(`dom_${id}`);
      }
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });
  });
});
const network = [];
page.on('request', request => network.push({
  method: request.method(), path: new URL(request.url()).pathname,
}));
try {
  await page.goto(url);
  await page.locator('#username').fill(username);
  await page.locator('#password').fill(password);
  await page.locator('#login').click();
  await page.waitForFunction(() => document.querySelector('#connection')?.textContent === 'Live');
  const initial = await page.locator('#rating-count').textContent();
  for (let idx = 0; idx < samples + 4; idx++) {
    const newRating = idx === samples + 3;
    const movie = newRating ? (Number(initial) === 0 ? 102 : 101) : (Number(initial) === 0 ? 101 : 1);
    await page.evaluate(purpose => { window.baseline.purpose = purpose; },
      newRating ? 'new_rating' : idx < 3 ? 'warmup' : 'measured');
    await page.locator('#movie').fill(String(movie));
    await page.locator('#stars').fill(String(1 + idx % 5));
    const before = await page.evaluate(() => window.baseline.sequence);
    await page.locator('#save-rating').click();
    await page.waitForFunction(previous => window.baseline.records.some(row =>
      row.operation === `${window.baseline.prefix}_${previous + 1}` && row.stage === 'paint_opportunity'), before);
    const notice = await page.locator('#notice').textContent();
    if (!notice.includes('Rating saved')) throw Error(`save failed: ${notice}`);
    const rating = await page.locator('#ratings').textContent();
    if (!rating.includes(`Movie ${movie}: ${1 + idx % 5} / 5`)) throw Error('rating mismatch');
    await page.waitForFunction(() => window.baseline.records.some(row =>
      row.operation === window.baseline.operation && row.stage === 'live_receive'));
    const result = await page.evaluate(() => window.baseline.records.filter(row =>
      row.operation === window.baseline.operation && row.stage === 'live_receive').at(-1));
    if (!result.cold_start) {
      const shown = await page.locator('#recommendations li span').allTextContents();
      const expected = result.recommendations.map(item => `Movie ${item.item_id + 1}`);
      if (JSON.stringify(shown) !== JSON.stringify(expected)) throw Error('live/render mismatch');
    }
  }
  const evidence = await page.evaluate(() => window.baseline.records);
  fs.writeFileSync(output, JSON.stringify({ url, username, initial, samples,
    warmups: 3, new_rating_samples: 1, errors, network, protocol, evidence }, null, 2));
  await page.screenshot({ path: output + '.png', fullPage: true });
  if (errors.length) throw Error(errors.join('\n'));
} finally {
  await browser.close();
}
