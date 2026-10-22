//===----------------------------------------------------------------------===//
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//===----------------------------------------------------------------------===//
// Browser-host behavioral regression, runnable with Node; no app or live server.
import assert from 'node:assert/strict';
import fs from 'node:fs';
const source = fs.readFileSync(new URL('../lib/glue/web/web.js', import.meta.url), 'utf8');
const calls = [];
globalThis.window = new EventTarget();
window.location = { search: '?api=http%3A%2F%2Flocalhost%3A8080' };
window.setTimeout = setTimeout;
window.clearTimeout = clearTimeout;
globalThis.XMLHttpRequest = class {
  open(...args) { this.args = args; }
  setRequestHeader(...args) { this.header = args; }
  send(body) {
    calls.push({ args: this.args, header: this.header, body });
    if (this.args[1] === 'broken') throw new Error('network');
    this.responseText = this.args[1] === 'denied' ? '{"error":"auth-failed"}' : '{"ok":true}';
  }
};
const sockets = [];
globalThis.WebSocket = class extends EventTarget {
  static CONNECTING = 0; static OPEN = 1;
  constructor(url) {
    super();
    if (url === 'broken') throw new Error('url');
    this.readyState = 0; this.bufferedAmount = 0; this.sent = []; sockets.push(this);
  }
  send(text) { if (this.failSend) throw new Error('send'); this.sent.push(text); }
  close(code) { this.closeCode = code; this.readyState = 3; this.dispatchEvent(new Event('close')); }
  message(data) { this.dispatchEvent(new MessageEvent('message', { data })); }
  open() { this.readyState = 1; this.dispatchEvent(new Event('open')); }
};
const host = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
for (const method of ['GET', 'POST', 'PUT', 'DELETE', 'HEAD']) {
  assert.equal(host.fetch_method('ok', method, '{"value":"é"}', 'application/json'), '{"ok":true}');
  assert.equal(calls.at(-1).args[2], false);
  assert.equal(calls.at(-1).body, ['GET', 'HEAD'].includes(method) ? null : '{"value":"é"}');
  assert.deepEqual(calls.at(-1).header, ['Content-Type', 'application/json']);
}
assert.equal(host.fetch_url('ok'), '{"ok":true}');
assert.equal(host.fetch_method('denied', 'POST', '', ''), '{"error":"auth-failed"}');
assert.equal(host.fetch_method('broken', 'POST', '', ''), '');
assert.equal(host.query_parameter('api', ''), 'http://localhost:8080');
assert.equal(host.query_parameter('missing', 'fallback'), 'fallback');
assert.equal(host.ws_open('broken'), 0);
const first = host.ws_open('ws://first'), second = host.ws_open('ws://second');
let notices = 0;
window.addEventListener('test-live', () => notices++);
assert.equal(host.ws_onmessage(first, 'test-live'), true);
assert.equal(host.ws_onmessage(9999, 'test-live'), false);
assert.equal(host.ws_send(first, 'early'), false);
sockets[0].open();
await Promise.resolve();
assert.equal(notices, 1);
assert.equal(host.ws_status(first), 1);
assert.equal(host.ws_send(first, 'rating'), true);
assert.deepEqual(sockets[0].sent, ['rating']);
sockets[0].message('one'); sockets[0].message('🌍'); sockets[1].message('foreign');
await Promise.resolve();
assert.equal(host.ws_pending(first), 2);
assert.equal(host.ws_receive(first), 'one');
assert.equal(host.ws_receive(first), '🌍');
assert.equal(host.ws_receive(first), '');
assert.equal(host.ws_receive(second), 'foreign');
sockets[0].bufferedAmount = 1048577;
assert.equal(host.ws_send(first, 'too much'), false);
sockets[0].bufferedAmount = 0; sockets[0].failSend = true;
assert.equal(host.ws_send(first, 'broken'), false);
sockets[0].dispatchEvent(new Event('error'));
assert.notEqual(host.ws_error(first), '');
sockets[0].close(1006);
await Promise.resolve();
assert.equal(host.ws_status(first), 3);
const beforeClose = notices;
host.ws_close(first);
sockets[0].message('stale');
await Promise.resolve();
assert.equal(notices, beforeClose);
assert.equal(host.ws_pending(first), 0);
assert.equal(host.ws_status(9999), 3);
assert.equal(host.ws_error(9999), '');
host.ws_close(9999);
sockets[1].message(new ArrayBuffer(8));
assert.equal(sockets[1].closeCode, 1009);
const overflow = host.ws_open('ws://overflow');
sockets[2].message('x'.repeat(1048577));
assert.equal(sockets[2].closeCode, 1009);
const full = host.ws_open('ws://full');
for (let index = 0; index < 129; index++) sockets[3].message('x');
assert.equal(sockets[3].closeCode, 1009);
host.ws_close(second); host.ws_close(overflow); host.ws_close(full);
let timers = 0;
window.addEventListener('test-timer', () => timers++);
host.event_cancel(host.event_after('test-timer', 5));
host.event_after('test-timer', 0);
await new Promise(resolve => setTimeout(resolve, 20));
assert.equal(timers, 1);
console.log('HTTP verbs/errors, WebSocket FIFO/isolation/limits/lifecycle and timer cancellation pass');
