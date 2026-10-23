# feat(net): HTTP/1.1 server + websocket framing stdlib (L3b/L3c)

## Summary

Two pure-Briev stdlib modules that let a Briev backend speak HTTP/1.1 to a browser and upgrade one path to a websocket:

- lib/std/net/http.bv - incremental HTTP/1.1 request parsing, response writers with permissive CORS, and the RFC 6455 websocket upgrade handshake.
- lib/std/net/websocket.bv - RFC 6455 frame decode (client to server, masked) and encode (server to client, unmasked).

Plus two small pure helpers used by the handshake:
- lib/std/net/sha1.bv, lib/std/net/base64.bv.

All pure Briev over the L1 ByteBuf/GrowBuf (bytes.bv) and the L2 socket (socket.bv). No C, no FFI in the protocol layer.

## Motivation

recommender-app Task 3 (net stack layers L3b/L3c). The app backend serves JSON to a browser frontend (cross-origin, hence CORS) and pushes live updates over a websocket. HTTP and websocket framing are the protocol layer between the raw L2 socket and the application.

## Design

### Incremental request parse (why NeedMore)

A TCP recv() delivers whatever bytes have arrived - maybe half a request, maybe one and a half. http_parse_request returns NeedMore until the full request (request line + headers + the Content-Length delimited body) has arrived, then Complete with the parsed request and the exact consumed byte count. The poll loop accumulates per connection and advances exactly consumed bytes, retaining any trailing bytes of the next (pipelined) request. The parser consumes EXACTLY one request and never over-reads - strict CRLF framing (the header terminator is the four bytes CR LF CR LF).

### Response writers + CORS

http_response(status, ctype, body) and http_json_response(status, body) build a complete HTTP/1.1 response into a GrowBuf. Every response carries permissive CORS (Access-Control-Allow-Origin: *, plus the methods/headers the frontend uses) so a cross-origin browser fetch and its OPTIONS pre-flight both succeed.

### Websocket upgrade handshake

ws_accept_key computes Sec-WebSocket-Accept = base64(SHA1(client_key + magic-GUID)). ws_handshake_response replies 101 Switching Protocols with that Accept header. After it is sent the connection speaks websocket framing, not HTTP. SHA1 and Base64 are the sibling pure helpers (sha1.bv, base64.bv).

### Websocket framing

ws_decode_frame decodes one client frame: opcode, FIN, the MASK bit + 4-byte masking key (client frames are ALWAYS masked - the server unmasks), and the 7/16/64-bit payload-length forms. It returns NeedMore until the whole frame has arrived, then Complete with the unmasked payload and the exact consumed length (same poll-loop discipline as the HTTP parser). ws_encode_text encodes a server text frame, UNMASKED (server frames must not be masked, RFC 6455 5.1), in the correct length form.

## Design notes

- Byte-level framing: http.bv does its own byte-oriented substring search and case-insensitive header compare over the raw payload, because HTTP framing is defined on BYTES (CR LF), not characters.
- String construction: the one place these modules poke bytes directly is assembling the languages own [len][bytes][NUL] String header to hand a freshly built buffer through the Data to String door (unmasked payloads, buffer slices). They do not reinvent framing.
- Opcodes are exposed (text/close/ping/pong) so the server loop routes policy; the framing module itself decides no policy.

## Dependency on fix branches

This feature WILL NOT COMPILE on main alone. It depends on three compiler fixes, each on its own branch cut from main:

- fix/lexer-cr-escape - http.bv/websocket.bv express CRLF framing as "\r\n" in String literals.
- fix/const-string-global - WS_MAGIC is a module-level const String.
- fix/dot-call-stateful-state - the response writers dot-call stateful GrowBuf members (put_bytes via grow_to_fit).

Recommended merge order: the three fix branches first (independent of each other), then this feature branch.

## Tests / verification

Scratch gate harnesses (not committed; under scratch/):
- ws_accept.bv: ws_accept_key("dGhlIHNhbXBsZSBub25jZQ==") returns s3pPLMBiTxaQ9kYGzzhZRbK+xOo= (RFC 6455 6.5.1 known vector).
- ws_roundtrip.bv: server encode -> decode round-trips; a masked client frame decodes (unmasks) to the original; the 16-bit length form (payload >= 126 bytes) round-trips.

brievc check clean on http.bv and websocket.bv.

## Files added

- lib/std/net/http.bv
- lib/std/net/websocket.bv
- lib/std/net/sha1.bv
- lib/std/net/base64.bv
