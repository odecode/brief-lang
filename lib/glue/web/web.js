// lib/glue/web/web.js — the browser host module.
//
// 2026-10-07 (host-boundary decision record, D7): the browser is a LIBRARY
// over the webstack target's host-import namespace. A `frgn ... from
// "lib/glue/web/web.js"` names this file; its `export const` bodies are
// inlined into the generated shim at module scope, and the frgn's wasm
// import stub calls them by name. No protocol hashword, no GLUE language
// target — this file IS the host module.

export const console_log = (msg) => console.log(msg);
export const console_warn = (msg) => console.warn(msg);
export const console_error = (msg) => console.error(msg);
export const set_text = (elem, text) => elem ? (elem.textContent = text) : 0;
export const get_element_by_id = (id) => document.getElementById(id);
export const performance_now = () => performance.now();
export const get_canvas = (id) => document.getElementById(id);
export const present_frame = (ctx) => ctx && ctx.present ? ctx.present() : 0;
// 2026-10-07: window.location.href is the FULL URL; route matching compares
// against the path form ("/about"), so the host returns the PATHNAME.
export const location = () => window.location.pathname;
export const navigate = (url) => history.pushState(null, 0, url);
// 2026-10-07: synchronous XHR — the Briev `fetch(url) -> String` binding is
// synchronous (lib/std/web/fetch.bv). Async fetch is a future enhancement.
export const fetch_url = (url) => {
  const xhr = new XMLHttpRequest();
  xhr.open('GET', url, false);
  xhr.send();
  return xhr.responseText;
};

// 2026-10-21: preserve the synchronous String-returning HTTP ABI. Browser
// callbacks below are separate notifications, never Promises returned to WASM.
// Replace XHR only when the language boundary supports suspended calls.
export const fetch_method = (url, method, body, contentType) => {
  try {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url, false);
    if (contentType) xhr.setRequestHeader('Content-Type', contentType);
    xhr.send(method === 'GET' || method === 'HEAD' ? null : body);
    return xhr.responseText;
  } catch (_) {
    return '';
  }
};

export const query_parameter = (name, fallback) =>
  new URLSearchParams(window.location.search).get(name) ?? fallback;

// 2026-10-21: the host owns native sockets; the application owns policy. Each
// handle has an independent bounded FIFO. Notifications use ordinary window
// events so existing b-window transactions consume them without compiler-known
// callback names. Explicit close releases the handle and cancels stale callbacks.
const webSockets = new Map();
let webSocketNext = 1;
const wsNotify = (handle) => {
  queueMicrotask(() => {
    const channel = webSockets.get(handle);
    if (channel?.event) window.dispatchEvent(new CustomEvent(channel.event, { detail: handle }));
  });
};
export const ws_open = (url) => {
  try {
    const socket = new WebSocket(url);
    const handle = webSocketNext++;
    const channel = { socket, event: '', messages: [], bytes: 0, error: '' };
    webSockets.set(handle, channel);
    socket.addEventListener('open', () => wsNotify(handle));
    socket.addEventListener('close', () => wsNotify(handle));
    socket.addEventListener('error', () => {
      channel.error = 'The live connection failed. Check the service address and retry.';
      wsNotify(handle);
    });
    socket.addEventListener('message', (event) => {
      if (!webSockets.has(handle)) return;
      const text = event.data;
      const size = typeof text === 'string' ? new TextEncoder().encode(text).length : 0;
      if (typeof text !== 'string' || channel.messages.length >= 128 || channel.bytes + size > 1048576) {
        channel.error = 'The live message exceeds the text or queue limit; reconnect.';
        socket.close(1009, 'text queue limit');
        wsNotify(handle);
        return;
      }
      channel.messages.push({ text, size });
      channel.bytes += size;
      wsNotify(handle);
    });
    return handle;
  } catch (_) {
    return 0;
  }
};
export const ws_onmessage = (handle, event) => {
  const channel = webSockets.get(handle);
  if (!channel) return false;
  channel.event = event;
  if (channel.socket.readyState !== WebSocket.CONNECTING || channel.messages.length) wsNotify(handle);
  return true;
};
export const ws_status = (handle) => webSockets.get(handle)?.socket.readyState ?? 3;
export const ws_pending = (handle) => webSockets.get(handle)?.messages.length ?? 0;
export const ws_receive = (handle) => {
  const channel = webSockets.get(handle);
  const message = channel?.messages.shift();
  if (!message) return '';
  channel.bytes -= message.size;
  return message.text;
};
export const ws_error = (handle) => webSockets.get(handle)?.error ?? '';
export const ws_send = (handle, text) => {
  const channel = webSockets.get(handle);
  if (!channel || channel.socket.readyState !== WebSocket.OPEN || channel.socket.bufferedAmount > 1048576) return false;
  try { channel.socket.send(text); return true; } catch (_) { return false; }
};
export const ws_close = (handle) => {
  const channel = webSockets.get(handle);
  if (!channel) return;
  webSockets.delete(handle);
  channel.socket.close(1000, 'client closed');
};
export const event_after = (event, delay) => window.setTimeout(
  () => window.dispatchEvent(new CustomEvent(event)), Math.max(0, delay));
export const event_cancel = (handle) => window.clearTimeout(handle);
