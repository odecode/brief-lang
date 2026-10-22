# Portable browser standard library

The browser target selects `plugins/parsed/prelude-web.bv` through target
configuration. This prelude registers portable types, collections, iterators,
casting and decimal formatting before user imports. `--no-stdlib` suppresses
this selection. Native process/environment/syscall lanes stay in the existing
`cast_lanes.bv` facade, which imports the shared `cast_portable.bv` definitions.
This is an import boundary, not a second implementation of casting.

Decimal conversion uses explicit Int64 accumulators and constants even when
the flexible Int register is 32-bit. JSON integer bounds follow physical Int
width; JSON finite-Float checks inspect fixed-width bits. `json_stringify`
encodes the parser's complete value algebra, validates Unicode, escapes control
bytes, rejects nonfinite numbers and limits recursive nesting to 64. The UTF-8
character-to-String buffer includes its eight-byte header and full payload.

Browser HTTP wrappers preserve the existing GET API and add method/body/content
type calls. WebSocket wrappers expose owned channel handles, bounded FIFO
messages, status, errors and close. Event helpers own cancellable timers and
query parameters. Host callbacks notify declared window events; Briev code owns
application transitions. HTTP currently returns synchronously through the String
ABI. See `applications/recommender-frontend.md` for limits and launch examples.

Native `read_file` owns its descriptor and closes it after either read outcome.
The regression fixture performs 512 reads under a 64-descriptor limit. Native
JSON fixtures and actual generated-WASM probes cover the portable boundary;
`tests/web_host_transport.mjs` checks HTTP errors, channel isolation, queue bounds,
closure and timer cancellation independently of the application.
