// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// Run against contract_gate.py's generated web directory served by HTTP.
import { createRequire } from 'node:module';
import { writeFile } from 'node:fs/promises';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const [url, output] = process.argv.slice(2);
if (!url || !output) throw new Error('Usage: contract_browser.mjs URL OUTPUT.json');
const browser = await chromium.launch({ channel: 'chrome', headless: true });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(url);
  await page.locator('#contract-result').filter({ hasText: /^(PASS|FAIL)$/ }).waitFor({ timeout: 120000 });
  const result = await page.locator('#contract-result').innerText();
  if (result !== 'PASS') throw new Error(`WASM protocol contract failed: ${result}`);
  if (errors.length) throw new Error(errors.join('\n'));
  const epochs = ['aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '0123456789abcdef0123456789abcdef'];
  await writeFile(output, JSON.stringify({ browser: browser.version(), result, executed_epochs: epochs, errors }, null, 2));
} finally {
  await browser.close();
}
