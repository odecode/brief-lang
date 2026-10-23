Implement task 12's native Briev backend: a nonblocking poll reactor, bounded
per-connection input/output, every HTTP API route, opaque-token authentication,
WebSocket upgrades and masked/fragmented live rating updates. Successful ratings
persist before prediction, and pushes reach only channels owned by that account.

The server constructs consistent baseline/account populations using a dense
account-ID map, materializes active-owner recommendations against a served cache,
and replaces complete models on periodic or explicit refresh. Failed refresh
retains the previous snapshot. GETs read owner results; partial writes preserve
unsent output under backpressure. HTTP responses close after draining; live
channels remain open until EOF, close or protocol/resource failure.

Build examples/recommender/server.bv and configure PGUSER, PGDATABASE and
UDATA_PATH. PORT=8080, MAX_CONNECTIONS=1024, LAMBDA_MILLI=500 and
REFRESH_SECONDS=300 are the defaults. Administration and trust authentication
remain the explicitly approved demo configuration. Full refresh is synchronous
between sweeps; performance targets remain task 16 gates.

The native runner checks database routing, real TCP/WebSocket isolation,
five-rating threshold, fragmented frames, ping/pong and protocol errors,
HTTP-triggered pushes, refresh mapping/failure, malformed framing, UTF-8 and JSON
boundaries, EOF/half-close, and 524292 exact bytes under forced backpressure.
Three proptest tests run 128 native cases each (properties 5,7,20).

Merge dependencies: collection-assignment-rebind and float-abs-intrinsic compiler
fixes first; JSON parser
progress/composition and HTTP status-text stdlib corrections separately. Keep
compiler/stdlib corrections out of the clean app-only feature branch. Detailed
ownership, wire format, bounds and verification evidence are documented in
docs/architecture/applications/recommender-server.md and its task-12 plan.
Interpreter changes are excluded as requested by the human.
