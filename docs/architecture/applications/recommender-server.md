# Recommender backend server

`examples/recommender/server.bv` is the native reactor entry. It creates the
schema, performs guarded baseline bootstrap and constructs a consistent engine
snapshot before listening. There is no authored main function. The perpetual
serve node calls one poll sweep at a time. All application/protocol/client code
is Briev; PostgreSQL is external infrastructure.

## Configuration and wire API

PostgreSQL is trust-authenticated on 127.0.0.1:5432 using PGUSER/PGDATABASE.
UDATA_PATH defaults to u.data. PORT defaults to 8080; MAX_CONNECTIONS to 1024;
LAMBDA_MILLI to 500 (0..1000 means lambda 0..1); REFRESH_SECONDS to 300.
Invalid configuration or failed bootstrap fails startup with a concrete error.

POST /register and /login accept username/password JSON strings; login returns
an opaque process-local token. POST /rating accepts token/item_id/rating and
performs an account-scoped upsert. GET /movies lists the zero-based movie IDs.
GET /state?token=... returns that owner's identity, ratings and recommendation
state. GET /recommendations?token=... returns cold_start:true below five distinct
ratings, or recommendations ordered by descending score and ascending item ID.
POST /admin/refresh schedules a snapshot rebuild; this demo endpoint has no
separate admin-auth scheme. OPTIONS responds with permissive CORS headers.

GET /live?token=... requires a version-13 WebSocket handshake with a valid
16-byte nonce. After upgrade, JSON text accepts item_id/rating. A token in the
frame never changes its connection owner. Successful HTTP or live ratings push
the owner's updated state to all of that owner's open channels only. Validation
errors go to the submitting channel. Ping receives Pong; Close is echoed.
Masked client frames, fragmented text and interleaved control frames are
supported. Invalid RSV/opcode/masking/length/UTF-8/fragment sequences close with
the appropriate protocol code. Binary messages are unsupported (1003).

## Ownership and scheduling

server_io.bv owns bounded raw input/output buffers. It reads or sends at most
one syscall's bytes per connection per sweep. EAGAIN/EINTR preserve progress.
Output queues retain their unsent suffix when another push arrives. HTTP sends
Connection: close and closes only after its output drains. The upgrade retains
any trailing frame bytes received with its HTTP headers. EOF preserves a queued
HTTP response; hard failures release the connection and its buffers.
An unusable listener/poll set fails the service with a flushed diagnostic rather
than spinning on a permanently failing descriptor.

Each connection has at most 64 KiB of accumulated input, 64 KiB of fragmented
text and 1 MiB of queued output. Exceeding a limit rejects/closes that peer.
HTTP framing rejects invalid/duplicate Content-Length and Transfer-Encoding;
JSON parsing rejects malformed grammar, duplicate application fields, noninteger
ratings and trailing input. JSON nesting is limited to 64 and integers to Int.
Slots, socket descriptors and buffer lifetimes belong to the single reactor;
copied Reactor/ServerModel values alias owned storage and must not be freed twice.

## Population and prediction state

server_model.bv reads baseline and account rows in one repeatable-read database
snapshot using bounded cursor pages. Accounts sorted by ID map to dense rows
after the 943 baseline rows. Deleted/skipped database IDs never become engine
indices. The served model owns its dual CSR population, means and two similarity
matrices. Ratings are capped at ten million per model for bounded allocation.

Login and rating changes materialize one owner's recommendation result. The
active row uses current persisted account ratings; its former snapshot row is
excluded from candidates, preventing self-neighbor duplication. Active user
similarities are computed once for that update, while item similarities and
neighbor means come from the immutable served cache. Serving a recommendation
reads its owner's materialized result rather than rebuilding matrices.

Explicit and periodic refreshes run between sweeps. A new model and all existing
owner views are built before the old model is freed. Failed refresh preserves
the previous model. This is synchronous single-process rebuilding; it may delay
socket servicing while running. Timings and 1000-channel capacity remain task 16
gates. No throughput or latency result is claimed here.

## Gates

`tests/fixtures/recommender/run_server.sh` builds native gates for API/DB
integration, reactor slots, malformed input, Unicode JSON, partial output under
forced backpressure, and register/login/rate-five/live ownership over real TCP.
The end-to-end gate uses two accounts and two channels for one owner, including
fragmented frames, a forged frame token, HTTP-triggered pushes, refresh and EOF.
It resets only briev_server_api_gate and briev_server_loop_gate schemas in a
dedicated test database. Do not run concurrent copies against that database.

The runner also executes the three tests in recommender_server_properties.rs:
128 proptest cases each for properties 5, 7 and 20, using a native Briev probe.
Interpreter checks are excluded by the user's explicit instruction.
