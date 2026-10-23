# Recommender I10/I11 integration

**Date:** 2026-10-23  
**Status:** implementation complete; Cargo test confirmation pending  
**Branch:** `recommender-proof-of-concept`

## Scope

I10 wires authenticated profile hydration, in-memory session validation, shared
HTTP/WebSocket admission, cached state reads, independent bounded persistence
and prediction dispatch, and correctly scoped publication into the reactor.
Hydration and receipt reconciliation must run off-loop. Persistence completion
must not trigger prediction or replace visible recommendations.

I11 connects the existing browser app to those live endpoints and events, then
verifies the generated WASM/host artifacts and a real browser flow while the
database write is blocked. The already implemented logout client flow also
needs its server token revocation and exact-token channel behavior.

## Verification and documentation

Use profile admission, operation store, worker process, server API/reactor and
browser pending gates with the dedicated recommender test database and isolated
ports. Add a native real-HTTP/WebSocket blocked-commit integration gate and run
the browser pending flow against that server. Update the recommender
account/server/frontend contracts. Do not make latency claims; controlled
responsiveness acceptance remains separate.

## Implementation log

- Initial inspection: standalone I04/I05/I07/I08/I09 components exist, but the
  live reactor still uses the synchronous legacy rating route and does not own
  admission or request worker-pool state. The task matrix defines I11 as the
  real browser/server flow; it is not a logout-only task.
- I11 server support: logout revokes only its opaque token and sends close 1008
  to channels authenticated by that token. The websocket gate drains the
  concatenated prior notification and close frame independently.
- Verification environment: ordinary WSL launch returned `Wsl/E_ACCESSDENIED`.
  The elevated WSL executor runs successfully. A dedicated temporary PostgreSQL
  cluster is running under `/tmp/briev-i10-i11-pg-20261023`, isolated from the
  application's existing database.
- I11 server verification: HTTP logout and reactor logout gates passed in the
  earlier session; `brievc check` passed for server, app, and both gates.
- 2026-10-23 continuation: the long `cargo test --lib` run was stopped at the
  user's request; do not report its result as verified. A release compiler
  rebuild completed. The persistence child now handles `login`,
  `register`, and `hydrate` messages using its own PostgreSQL connection, and
  validates/returns an opaque login token plus the owner's initial ratings.
  `session_adopt` provides the parent's validated token-binding primitive.
  These are worker capabilities only: the reactor dispatch/reply coordinator,
  I10 admission path, `/v1/ratings` and operation-status routes, and I11 live
  browser/server gate remain to be wired before claiming either task complete.
- Verification after cleanup: `cargo build --release` succeeded. The rebuilt
  compiler passed `brievc check` for the server, app, worker contract, session
  gate, API gate, and reactor gate; it generated `sessions_gate`,
  `worker_contract_checks`, `worker_process_gate`, `server_api_gate`, and
  `server_loop_gate` successfully. Their runtime tests and the full Cargo suite
  were not run in this continuation, per the user's instruction to confirm
  tests later.
- I11 real-browser harness: `browser_live_server.mjs` and
  `run_i11_browser.py` build app/server from the current checkout, record
  source/artifact hashes, and hold an account-row lock across pending and
  recommendation paints. Syntax checks passed. The live gate awaits completion
  of I10's real routes and worker coordinator.
- Current integration pass: the reactor now starts one persistence and one
  prediction child, sends login/register and rating jobs asynchronously,
  validates replies against their tags, and routes accepted, recommendation,
  saved, failed, and discard events to authenticated owner channels. HTTP and
  WebSocket ratings share admission. Cached state includes the current profile
  revision and retained operation summaries; retry/discard endpoints are
  wired. `brievc check examples/recommender/server.bv` passes.
- Follow-up corrections: server startup now applies the durable operation
  receipt-table migration after the account/rating schema. The persistence
  failure encoder extracts the operation ID from either the top-level discard
  payload or nested rating command, so SQL failures remain typed events. A
  compiler state-write fix preserves returned members of a top-level unpacked
  server object while leaving local object assignments local. Persistence
  replies return directly through the coordinator transition so polling the
  prediction child cannot overwrite the newly advanced state.
- I11 manual browser integration: the app was rebuilt/served against the
  dedicated PostgreSQL cluster. With account 20 row-locked, rating movie 6 as
  2 immediately rendered as pending and fresh recommendations rendered while
  the save was blocked. After COMMIT, the UI reported “Rating saved,” cleared
  pending status, and PostgreSQL contained the updated rating and durable
  receipt. An unlocked save was also confirmed. The automated Playwright runner
  was not run because Playwright is unavailable in the environment.
- The old `/rating` API remains a synchronous compatibility handler. The
  one-worker-per-role configuration rejects additional simultaneous ratings
  with 503.
- Final checks: `brievc check examples/recommender/server.bv`,
  `brievc check examples/recommender/app.rbv`, and
  `brievc check tests/fixtures/recommender/worker_contract_checks.bv` pass. The
  final native server and split WASM app artifacts build successfully. Cargo
  tests were not run per the user's instruction; confirmation remains pending.
