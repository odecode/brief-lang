//===----------------------------------------------------------------------===//
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//===----------------------------------------------------------------------===//
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname, basename } from 'node:path';
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = resolve(process.argv[2] || 'target/collection-crash-web');
const server = createServer(async (request, response) => {
  const name = basename(new URL(request.url, 'http://localhost').pathname);
  try {
    const bytes = await readFile(resolve(root, name));
    response.writeHead(200, { 'content-type': { '.html': 'text/html', '.mjs': 'text/javascript', '.wasm': 'application/wasm' }[extname(name)] || 'text/plain' }).end(bytes);
  } catch { response.writeHead(404).end(); }
});
await new Promise(done => server.listen(0, '127.0.0.1', done));
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge', headless: true });
try {
  const page = await browser.newPage();
  page.setDefaultTimeout(15000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/collection_snapshot.html`);
  await page.getByText('世界', { exact: true }).waitFor();
  assert.deepEqual(await page.locator('li').allTextContents(), ['héllo', '世界']);
  await page.getByRole('button', { name: 'Grow', exact: true }).click();
  await page.waitForFunction(() => document.querySelectorAll('ul li').length === 1100);
  assert.equal(await page.locator('ul li').first().innerText(), '0');
  assert.equal(await page.locator('ul li').last().innerText(), '1099');
  assert.deepEqual(await page.locator('ol li').allTextContents(), Array.from({ length: 12 }, (_, index) => `Row ${index}`));
  await page.getByRole('button', { name: 'Reset', exact: true }).click();
  await page.waitForFunction(() => document.querySelectorAll('ul li').length === 0);
  assert.deepEqual(errors, []);
  console.log('collection snapshots: Unicode, empty initialization, 1100 rows, generic struct concatenation, reset pass');
} finally {
  await browser.close();
  await new Promise(done => server.close(done));
}
