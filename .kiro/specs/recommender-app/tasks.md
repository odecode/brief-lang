# Implementation Plan: Recommender App (paper-faithful AutAI-Fusion CF, pure Briev)

## Compiler fix branches — 2026-11-02

All five branches are cut from fork/main b85f953d and pushed to fork. PR body documents are untracked root artifacts. Merge callable-transaction-emission before browser-transaction-publication. Keep all distinct tests and BUGS entries when resolving append conflicts.

- `fix/enum-object-layout` — `90e71eeb`; PR body: `PR-enum-object-layout.md`.
- `fix/enum-field-constructor-context` — `6a09f605`; PR body: `PR-enum-field-constructor-context.md`.
- `fix/enum-object-projection-lifetime` — `9c4b77c6`; PR body: `PR-enum-object-projection-lifetime.md`.
- `fix/callable-transaction-emission` — `f1d79cf1`; PR body: `PR-callable-transaction-emission.md`.
- `fix/browser-transaction-publication` — `e7dec709`; PR body: `PR-browser-transaction-publication.md`.

Final gates: every isolated branch passed its focused regressions; Praetor comparison found no new diagnostics. Full suites reported only the accepted SPIR-V environment failures after addressing a CRLF-sensitive adapters.dbvl checkout issue. The first three suites recorded that conformance failure; LF normalization (no Git content diff) and targeted brievc checks passed. The final two suites passed conformance. No app changes were included in these branches.


## Overview

This plan turns the approved [design](./design.md) into small, incremental,
test-driven coding tasks. It builds the Briev net stack bottom-up (the layer
cake in the design's Architecture section — L2 sockets → L3a Postgres → L3b/L3c
HTTP+websocket) and then the application on top (the AutAI-Fusion CF engine, the
similarity cache, the parser/schema/bootstrap, the account service, the poll
event-loop server, the frontend, the load simulator), closing with performance
verification. Each layer is made testable before the next layer depends on it, so
there is no big-bang integration at the end — the final tasks only wire together
pieces that already run and are tested in isolation.

Correctness is measured against the **Reference_Algorithm** (the AutAI-Fusion
paper) via an **independent scratch verifier / hand-worked small example**, NOT
against `recommender_singlepass.cpp` (that C++ file is a performance baseline only
and carries three defects the engine must not reproduce — see Requirement 4 and
the design's CF Engine section).

Confirmed design decisions (all five open items resolved by the user):
single-process `poll` event loop now (epoll later if needed); **4×** the C++
baseline for the prediction phase; λ default **0.5**, environment-configurable,
held-out validation an optional stretch; **64-bit** `Float` for first-green;
Postgres **`trust`** auth for first-green (md5 the documented next step, SCRAM
deferred).

Read [WORKFLOW.md](./WORKFLOW.md) first — it governs the teaching cadence and the
Windows-source / WSL-build environment split, and holds the exact brievc
invocations and the branch/PR flow referenced below. Then skim
[requirements.md](./requirements.md) and [design.md](./design.md).

---

# START HERE (fresh-session orientation)
## Current load checkpoint — COMPLETE 2026-11-05

- Application commit: `ac7ffa7` in `../recommender-app`.
- Use clean compiler worktree `../recommender-compiler-carveouts/load-transport-verified`, branch `integration/load-transport-verified`, commit `044192d4`. Pinned WSL binary: `/home/otto/briev-load-tools/transport-brievc-final`.
- PR #65 tuple values: `fix/tuple-value-types` / `05d8aef7`; https://github.com/Randozart/briev-lang/pull/65.
- PR #66 lifetime proofs: `fix/socket-borrowing-effects` / `59ec602e`; https://github.com/Randozart/briev-lang/pull/66.
- PR #67 transport stdlib: `feat/nonblocking-client-transport` / `1eb1d3a0`; https://github.com/Randozart/briev-lang/pull/67.
- Integration includes earlier collector PRs #63/#64 and upstream `2d9d37b7`. Local and fork main were synced to that upstream commit.
- Final gates: 3,505 library tests, five native integrations, wasm32 execution, ten-program IR determinism, four transport Valgrind/descriptor probes, eleven rejection cases, and full collector readiness all pass. Collector preflights: 2×5,000 samples, flat post-warmup RSS 369/365 pages, VM 3,989,504 bytes, zero missed arrivals.
- Source conformance sweep remains delegated to CI. Kani cannot start on this WSL glibc. All three Clang 17/18 corpus programs execute and have identical semantic output; the raw matrix comparator falsely differs on printed elapsed-time values. Detailed evidence and limits: `../recommender-app/docs/plans/2026-11-05-controlled-transport-checkpoint.md`.
- Next checkpoint: one bounded HTTP journey attached to arrival scheduling and attempt outcomes. No server capacity claim yet.
- Preserve the original dirty compiler and pre-existing app edits. The old `load-collector-prerequisites` worktree is now on `integration/load-transport-development` with exploratory changes; use the clean verified worktree above.


Read [WORKFLOW.md](./WORKFLOW.md) first (environment split + the branch/PR
integration flow), then this block, then the requirements/design.

## This is a teaching build — work in SMALL increments
Per WORKFLOW.md's prime directive: do ONE sub-step, STOP, explain what was built,
HOW it works, and WHY, then verify its gate, then move on. Do not one-shot a
module and test at the end. Keep the human in the loop and in overview.

## The environment split (summary — WORKFLOW.md is authoritative)
- SOURCE OF TRUTH: the Windows tree at `c:\Users\wotto\code\briev-lang`
  (`/mnt/c/Users/wotto/code/briev-lang` from WSL). Author all code and docs here.
- BUILD/TEST EXECUTOR: WSL. Compile with the WSL `brievc`; the build cache +
  binary live on the native Linux fs via `CARGO_TARGET_DIR` (drvfs mtime churn
  otherwise forces full rebuilds).
- The exact pinned commands (check / build / run, the compiler rebuild, and
  `cargo test --lib`) are in WORKFLOW.md's "Build and test strategy" and the
  prior effort's Commands section — DO NOT invent commands; use those invocations.

## Standing gates (every code step)
- `brievc check` the changed `.bv` source (fast typecheck inner loop).
- If testable in isolation, build + run a tiny `.bv` harness and show output
  (runtime verification — some layout facts, e.g. the String header offset, only
  surface by RUNNING, not by `check`).
- For a compiler Rust change: `cargo test --lib` green and `brievc check` on the
  repro.
- Praetor on each changed directory: `praetor validate --warn --target <dir>`
  (`--target` is a DIRECTORY, never a file).

## Branch / PR carve-out flow (summary — WORKFLOW.md is authoritative)
- `feat/recommender-app` (or the existing vessel) is the working surface.
- When a logical piece is done, CARVE IT OUT into a clean branch cut from `main`
  containing ONLY that piece's files, and open a PR with a `PR-<topic>.md` body
  at the repo root. A compiler fix goes on its OWN `fix/<name>` branch from main
  with its regression test + a `BUGS.md` entry, PR'd separately; keep stdlib work
  moving on a TEMP `integration/<topic>` branch (never PR'd) while fixes are in
  flight.

## ⚠ CROSS-CUTTING RULE — compiler-bug discipline (Req 9.7 + operating contract)
This is NOT a task; it governs EVERY task below. When any task surfaces a Briev
compiler bug or a language gap, you MUST:
1. **Reproduce minimally** — a scratch probe under `scratch/`, ideally a
   controlled A/B that isolates the trigger.
2. **Fix it on the compiler side** on its own `fix/<name>` branch from `main`,
   with a regression test; `cargo test --lib` green.
3. **Log it in `BUGS.md`** (OPEN → FIXED <date> + the one-line root cause and
   fix) and in the net-stack plan's bug log.
4. **NEVER work around it in the stdlib.** The interpreter is the reference; fix
   codegen, not the `.bv`. (The prior effort already found and fixed four this
   way: undeclared `llvm.memcpy`, `Alloc#` vs `Malloc#`, liveness member-name
   collision, and type-dependent trait-default state — mirror that discipline.)

The design's **Compiler / Language Risk Ledger** names the highest-risk areas;
tasks that touch them carry a `⚠ RISK` note so you expect the bug and keep the
minimal `.bv` repro under test as a regression guard:
- Large `Malloc#`-backed Float arrays at scale (~30 MB matrices, 8-byte-stride
  `Load#`/`Store#`).
- Float math intrinsics (`Sqrt#`, native float division; zero-variance / zero-η /
  NaN edges) — verify the OPTIMIZED IR, not just outputs.
- The reactor + many sockets (long-lived poll loop, non-blocking I/O, timer,
  pointer-swap refresh).
- `frgn` glue for the frontend (`glue/web/web.js`, `src/glue/web_generator.rs`).
- Parameterized Postgres wire encoding (byte framing, length backpatch by OFFSET
  not cached pointer, bind-parameter encoding).
- Trait defaults with state (the `ByteSink` default methods over per-implementer
  required methods — a known prior fragility, exercised hard by `pg.bv`/`http.bv`).

## Prerequisite already in place
L1 `lib/std/net/bytes.bv` (the `ByteSink` trait: fixed `ByteBuf` + growing
`GrowBuf` sharing the derived `put_u16_be`/`put_u32_be`/`put_cstr` writers) and
`lib/std/posix/syscall.bv` (the variadic `syscall(nr, ...)` over `SysCall#` with
the socket/poll/clock numbers) both exist. `lib/std/json.bv` is usable. The net
stack starts at L2 (sockets).

---

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `*` = optional test sub-task
(do NOT implement unless asked). Each task lists its concrete gate and the
requirement clauses it implements.

## Tasks

- [x] 1. L2 — `lib/std/net/socket.bv`: TCP client over raw syscalls
  _Design: The Net Stack To Build → socket.bv. ⚠ RISK: reactor + many sockets (foundation)._
  - [x] 1.1 `sock_tcp()` + `sock_close`/`sock_shutdown`
    - `socket(AF_INET=2, SOCK_STREAM=1, 0)` via `SYS_SOCKET=41`; hold the fd in
      `obj Socket { fd: Int; }`; `-errno` convention on failure. Close via
      `SYS_CLOSE`, shutdown via `SYS_SHUTDOWN=48`.
    - _Requirements: 9.2, 8.4_
    - DONE: fd wrapped in `obj Socket`; `-errno` flows through the obj
      (callers test `s.fd < 0`); postconditions pin the `>= -4096` error domain.
  - [x] 1.2 Build the 16-byte `sockaddr_in` with a fixed `ByteBuf`
    - family LE (offset 0), port BE (offset 2), addr BE (offset 4), 8 zero pad;
      draw the byte layout. Reuses the L1 `ByteSink` writers.
    - _Requirements: 9.2_
    - DONE: `make_sockaddr_in` + `pad_zeros` + `ip_v4`/`LOOPBACK`. LESSON:
      the L1 writers are called FREE-FUNCTION style (`put_u8(buf, v)`) over a
      WHOLE-module `import "std/net/bytes.bv"` — a selective `import { put_u8 }`
      binds the bodyless `ByteSink` trait decl (Self→Int), not the ByteBuf
      member. (Dot form `buf.put_u8(v)` surfaced a typechecker bug — see
      compiler-fix note below.)
  - [x] 1.3 `sock_connect(s, addr, port)` via `SYS_CONNECT=42`
    - pointer+length ABI for passing the struct to the kernel; connect to
      `127.0.0.1:PORT`.
    - _Requirements: 9.2_
    - DONE: passes `sa.ptr` + `SOCKADDR_IN_LEN=16`; frees the scratch ByteBuf
      after the kernel copies the struct. Verified rc=0 to loopback.
  - [x] 1.4 `sock_send`/`sock_recv` partial-transfer loops
    - loop until the full buffer moves; `recv == 0` is EOF, negative is `-errno`
      surfaced as an error distinct from EOF.
    - _Requirements: 9.2_
    - DONE: tail-recursive `send_loop`/`recv_loop` (the fs.bv short-count
      pattern). recv 0 ⇒ EOF (returns bytes so far); recv < 0 ⇒ -errno returned
      directly, distinct from EOF.
  - [ ]* 1.5 Integration test: loopback socket round-trip
    - a tiny `.bv` harness connects to a local listener (or pairs with 1.7) and
      moves bytes both ways; assert the bytes received equal the bytes sent.
    - _Requirements: 9.2_
    - NOTE: not implemented as a committed test (optional `*`), but the FINAL
      GATE harness `scratch/sock_loopback.bv` exercises exactly this and prints
      `roundtrip_ok=true` (one byte client→server over loopback).
  - [x] 1.6 `sock_set_nonblocking` (`SYS_FCNTL`) + `SO_REUSEADDR` (`SYS_SETSOCKOPT=54`)
    - non-blocking so no one connection blocks the later poll sweep; REUSEADDR on
      the listener.
    - _Requirements: 9.2_
    - DONE: `sock_set_nonblocking` does the correct F_GETFL→OR O_NONBLOCK→F_SETFL
      sequence (never clobbering other flags); `sock_set_reuseaddr` builds a
      4-byte LE optval=1 and passes its pointer+len to setsockopt.
  - [x] 1.7 Server side: `sock_bind_listen` (`SYS_BIND=49`+`SYS_LISTEN=50`) + `sock_accept` (`SYS_ACCEPT=43`)
    - the listen backlog; accept returns a NEW fd per connection.
    - _Requirements: 9.2_
    - DONE: `sock_bind_listen` sets REUSEADDR, binds INADDR_ANY:port, listens with
      the backlog; `sock_accept` returns a NEW `Socket` per connection (verified
      server_fd=5 distinct from listener_fd=3).
  - Gate: `tcp_connect` to `127.0.0.1` returns a valid fd and send/recv moves
    bytes; `bind_listen`+`accept` round-trips a byte on loopback; `brievc check`
    clean; any oddity logged per the cross-cutting rule.
    - ✅ MET: `scratch/sock_loopback.bv` prints `bind_listen rc=0 listener_fd=3`,
      `connect rc=0 client_fd=4`, `accept server_fd=5`, `sent=1`,
      `recv_count=1 byte=65`, `roundtrip_ok=true`. `brievc check` clean on
      `socket.bv`.
    - ⚠ COMPILER FIXES (Req 9.7, both reproduced under `scratch/`, fixed on the
      compiler side with `cargo test --lib` regression tests, logged in BUGS.md —
      NOT worked around in the stdlib):
      1. Typechecker: dot-method dispatch `buf.put_u8(x)` to an EXPLICIT-receiver
         obj member misaligned args by the receiver (`resolve_method_call` didn't
         skip the self param). Fixed + 2 tests. (socket.bv uses the free-function
         form regardless, which is the canonical idiom.)
      2. Backend: a user defn declared `-> Void` called as a bare statement
         emitted invalid IR `%t = call void @f(...)` (the void guard keyed only on
         an EMPTY return list, missing explicit `-> Void`). Fixed + 1 test.

- [x] 2. L3a — `lib/std/db/pg.bv`: PostgreSQL v3 wire client
  _Design: The Net Stack To Build → pg.bv. ⚠ RISK: parameterized PG encoding; trait-default state (ByteSink over GrowBuf). Depends on Task 1._
  - [x] 2.1 Message framing: write `type:u8 | len:i32be | payload`, read `type + i32be len + (len-4) payload`
    - the universal post-startup frame; length counts itself but not the type
      byte. Length backpatch records an OFFSET into a fixed `ByteBuf`, never a
      cached interior pointer (GrowBuf move hazard).
    - _Requirements: 9.3_
    - DONE: `pg_send_msg` assembles the whole frame into a FIXED ByteBuf sized to
      the exact total (no GrowBuf move hazard); `pg_read_msg` reads the 5-byte
      header then the `len-4` payload. ✅ GATE: `scratch/pg_encode.bv` verified the
      'Q' frame byte-for-byte (type=81, len=13, payload "SELECT 1"+NUL).
  - [x] 2.2 `StartupMessage` encode + send (protocol 3.0, user+database NUL pairs)
    - the one message with NO type byte (`len:i32be | protocol:i32be | params`).
    - _Requirements: 9.3_
    - DONE: `pg_send_startup` (protocol 196608, `user`/`database` cstr pairs + a
      terminating NUL), length into a fixed ByteBuf.
  - [x] 2.3 Trust-auth handshake: read `AuthenticationOk (R,0)`
    - first-green uses server `trust` auth → `AuthenticationOk` immediately. Note
      md5 (`md5(md5(pass+user)+salt)`) as the documented next step; SCRAM deferred.
    - _Requirements: 9.3_
    - DONE: `pg_handshake` reads 'R', treats code 0 as AuthenticationOk; any
      non-zero auth code is a first-green-unsupported signal (pid=-1). md5/SCRAM
      noted in-source as next steps.
  - [x] 2.4 Drain to `ReadyForQuery ('Z')`: consume `ParameterStatus`/`BackendKeyData`
    - loop until the server says ready before issuing queries.
    - _Requirements: 9.3_
    - DONE: `pg_handshake` loops, recording BackendKeyData (pid/key), skipping
      ParameterStatus, until 'Z'.
  - [x] 2.5 Simple Query `'Q'`: `SELECT 1`; parse `RowDescription 'T'`, `DataRow 'D'`, `CommandComplete 'C'`
    - text-format columns.
    - _Requirements: 9.3_
    - DONE: `pg_simple_query` + `pg_read_result` pump; RowDescription sets ncols,
      DataRow decodes text fields, CommandComplete skipped, loop ends at 'Z'.
  - [x] 2.6 Row model + typed accessors `pg_row_int`/`pg_row_text`
    - decode a `DataRow` text field into Briev values.
    - _Requirements: 9.3_
    - DONE: `PgResult` holds row-major `List<String>` text fields + shape;
      `pg_row_text(r,c)` / `pg_row_int(r,c)` (via `to_int`), bounds-contracted.
      SQL NULL (len -1) decodes to "".
  - [x] 2.7 Extended Query (parameterized): `Parse`/`Bind`/`Describe`/`Execute`/`Sync`
    - the scope bar — bound params, never string-interpolated (injection-safe,
      operating-contract secure-by-default). Teach why parameterized queries exist.
    - _Requirements: 9.3, 8.2_
    - DONE: `pg_exec` sends the full P/B/D/E/S sequence; params bound as text
      values (`pg_build_bind`/`pg_bind_values`). ✅ GATE: `scratch/pg_encode.bv`
      verified the Bind payload byte-for-byte for `["alice","42"]`.
  - [x] 2.8 CRUD wrappers over `pg_exec`: `INSERT ... RETURNING`, `UPDATE`, `DELETE`, `SELECT`
    - plus `ErrorResponse 'E'` parsing into a Briev error carrying SQLSTATE+message.
    - _Requirements: 9.3_
    - DONE: `ErrorResponse 'E'` parsed into `PgResult.err_code` (SQLSTATE 'C') +
      `err_msg` ('M'), ok=false. The CRUD statements themselves are one-line
      `pg_exec(c, "<SQL with $n>", [params])` calls the app layer (Tasks 10/11)
      issues with its real SQL — the mechanism (bound params + error carry) is here.
  - [ ]* 2.9 Integration test: connect/auth/simple+parameterized query against a test PostgreSQL (trust auth)
    - document the local PG setup (pg_hba trust, a scratch DB+table); `SELECT 1`
      prints 1; a parameterized `SELECT` returns typed rows; CRUD runs.
    - _Requirements: 9.3_
  - Gate: connect + `SELECT 1` → 1; parameterized `SELECT` returns typed rows; CRUD
    statements run against the test table; every message type documented.

- [x] 3. L3b/L3c — `lib/std/net/http.bv` (HTTP/1.1 + WS upgrade) and `lib/std/net/websocket.bv` (frames)
  _Design: The Net Stack To Build → http.bv / websocket.bv. ⚠ RISK: trait-default state. Depends on Task 1._
  - [ ] 3.1 Incremental request parse: request line + headers + `Content-Length` body
    - strict CRLF framing; `http_parse_request` returns `NeedMore` until the full
      request (headers + declared body) has arrived, so it composes with the poll
      loop and never over-reads into the next request.
    - _Requirements: 9.4_
  - [ ] 3.2 Response writers: `http_response(status, ctype, body)` + `http_json_response` with CORS
    - `application/json` + permissive CORS (`Access-Control-Allow-Origin: *`) so
      the browser frontend can call cross-origin.
    - _Requirements: 9.4_
  - [ ] 3.3 Websocket upgrade handshake in `http.bv`: `Sec-WebSocket-Accept = base64(SHA1(key + magic-GUID))`
    - small pure `sha1`/`base64` helpers on `bytes.bv`; reply `101 Switching
      Protocols`.
    - _Requirements: 9.5_
  - [ ]* 3.4 Unit test: `Sec-WebSocket-Accept` known vector
    - the RFC 6455 example key → expected accept string (example test, not PBT).
    - _Requirements: 9.5_
  - [ ] 3.5 `websocket.bv` frame decode: opcode, MASK bit + 4-byte key (unmask client frames), 7/16/64-bit length
    - _Requirements: 9.5_
  - [ ] 3.6 `websocket.bv` frame encode: `ws_encode_text` server→client, unmasked, correct length form
    - _Requirements: 9.5_
  - [ ]* 3.7 Property test — Property 23: Websocket frame round-trip
    - **Feature: recommender-app, Property 23: for any text payload, decoding an
      encoded frame (incl. the client masking path) reproduces the original
      payload exactly.** min 100 iterations.
    - _Validates: Requirements 9.5_
  - [ ]* 3.8 Integration test: HTTP request/response over loopback
    - a `.bv` client GETs and the server returns a JSON 200 parsed back correctly.
    - _Requirements: 9.4_
  - Gate: a request is parsed incrementally and a JSON+CORS 200 returned; the
    known-vector accept matches; frame encode/decode round-trips (incl. mask).

- [x] 4. Matrix/Vector/IntVec primitives (`Malloc#`-backed flat arrays)
  _Design: Data Models → Matrix and Vector. ⚠ RISK: large Malloc# Float arrays; float load/store intrinsics._
  - [x] 4.1 `obj Matrix {ptr;rows;cols}` + `mat_get`/`mat_set` with bounds contracts
    - element `(r,c)` at byte offset `(r*cols+c)*8`; `LoadF#`/`StoreF#` (resolve
      the exact float load/store intrinsic via `get_intrinsic_signature()`; fall
      back to `Load#`/`Store#` + a `Cast.#` reinterpret of the 8-byte slot only if
      no float-typed intrinsic exists). Intrinsics-before-`frgn`.
    - _Requirements: 4.2, 4.6, 9.1_
    - DONE: `lib/std/matrix.bv`. RESOLUTION: no `LoadF#`/`StoreF#` exists in
      `get_intrinsic_signature()` (checked `src/intrinsic_signatures.rs`: `Load#`
      is `Native("Int")`, `Store#` untyped). Rather than a manual Float↔bit
      reinterpret, cast the Int address to `Ptr<Float>` and use native typed
      indexing (`base[r*cols+c]`) — a real f64 load/store, no intrinsic, matches
      the working `benchmarks/recommender.bv` pattern. `brievc check` clean.
  - [x] 4.2 `obj Vector {ptr;len}` + `vec_get`/`vec_set`; `obj IntVec` twin at 8-byte stride
    - the `IntVec` is named explicitly so index arrays never silently reuse the
      float `Vector` (no float round-trip of integer offsets).
    - _Requirements: 4.1, 4.5_
    - DONE: `Vector` via `Ptr<Float>`; `IntVec` via `Ptr<Int>` (integer bits, no
      f64 encoding). Gate proved IntVec holds 2^53+1 exactly — the reason it is a
      distinct type. ✅ GATE MET: `scratch/matrix_rt.bv` prints every round-trip
      `ok=true`, incl. a 1682×1682 (~2.83M float, ~22.6MB) allocate/round-trip/free
      (the risk-ledger large-Malloc path). Not committed (scratch is gitignored,
      per the Task-1/3 convention). Praetor N/A (no Rust changed; `.bv` only).
  - [ ]* 4.3 Unit test: allocate a ~2.83M-float matrix, store/load at scale, free
    - exercises the large-allocation + 8-byte-stride path that the risk ledger
      flags; confirm values round-trip and the IR load/store is correct.
    - _Requirements: 9.1_
  - Gate: `mat_get(mat_set(m,r,c,v)) == v` for in-bounds `(r,c)`; a full item-item
    sized block allocates, round-trips, and frees; `brievc check` clean.

- [x] 5. Sparse `RatingPopulation` (dual orientation) + the independent reference verifier
  _Design: Data Models → Sparse rating population; Testing Strategy → independent reference._
  - [x] 5.1 Build `RatingPopulation` (per-user rows AND per-item columns) in one pass
    - CSR-style `*_off`/`*_item`/`*_user`/`*_val` over `Vector`/`IntVec`; 
users`,
      
items`, 
nz`. Both orientations from one scan (user side for Eq. 29, item
      side for Eq. 30).
    - _Requirements: 4.4, 4.8_
    - DONE: `lib/std/rating_population.bv` — counting-sort CSR both ways
      (`pop_build` → `csr_build` for user- and item-orientation) over IntVec
      offsets/indices + Vector values; `pop_user_begin/end`, `pop_item_begin/end`
      accessors. ✅ GATE: `scratch/rating_pop_rt.bv` round-trips a known 6-rating
      set in both orientations (per-user and per-item counts + value sums match).
      ⚠ COMPILER FIX (Req 9.7): surfaced the Malloc# CSE-alias double-free —
      fixed on `fix/malloc-raw-memory-attr` (merged to main via PR; also on the
      vessel), BUGS.md logged.
  - [x] 5.2 The independent scratch reference: the paper equations + a hand-worked 4×4 example
    - a direct, obviously-correct implementation of the AutAI-Fusion equations
      (means, PCC, Eq. 7/§3.2 imputation, Eq. 29/30, Eq. 31) over a tiny dense
      population, plus the hand-worked 4-user×4-item fixture with known outputs.
      This is the correctness oracle for Tasks 6–8 — NOT the C++.
    - _Requirements: 4.1, 4.4, 4.8, 4.13_
    - DONE: `examples/recommender/reference.bv` — dense straight-from-the-paper
      means / PCC (Eq. 9, zero-variance→0) / user-based prediction (Eq. 29) /
      fusion (Eq. 31) + [1,5] clamp, over the hand-worked 4×4. ✅ GATE: every
      value checks out — u0_mean=4.0, u1=2.25, u2=3.5, u3=3.6667; sim(u0,u1)=
      0.852803 (matches hand arithmetic), PCC symmetric, sim(u0,u0)=1.0;
      predict_user(u3,i3)=3.1667, fused(λ=0.5)=3.25 ∈[1,5]; clamp edges 1.0/5.0.
      ⚠ COMPILER FIX (Req 9.7): surfaced the Float-tuple destructure i64 miscompile
      — fixed on the vessel (`fix/float-tuple-destructure` carve-out), BUGS.md logged.
  - Gate: the population round-trips a known rating list in both orientations; the
    scratch reference reproduces the hand-worked 4×4 example's known values. ✅ MET.

- [ ] 6. CF_Engine part 1 — means, imputation, PCC similarity
  _Design: The CF Engine → Means / Key-set imputation / PCC. ⚠ RISK: Sqrt#/float division, zero-variance/NaN. Depends on Tasks 4, 5._
  - [x] 6.1 True `User_Mean` ūa and `Item_Mean` t̄s (+ `has_mean`, global-mean fallback)
    - true arithmetic average of observed ratings; NO degenerate constant
      (corrects C++ defect #1).
    - _Requirements: 4.1, 4.5_
    - DONE: `examples/recommender/cf_engine.bv` (APP code, NOT stdlib — the paper
      equations are app knowledge; only the Vector/IntVec/CSR primitives are
      stdlib). `obj Means` holds both mean vectors + per-row `has` flags + the
      global mean. Each mean is ONE contiguous CSR slice-sum over
      `pop_user_begin/end` (resp. item) — the sparsity already encodes
      "observed", so no dense per-cell `observed()` test (O(nnz), not
      O(users×items)). Empty row ⇒ global-mean fallback + has=0 (never a
      degenerate constant). ✅ GATE MET: the harness loads the oracle's 4×4 (15
      observed cells, u3/i3 missing) and every mean matches reference.bv within
      1e-6: u0=4.0 u1=2.25 u2=3.5 u3=3.666667; i0=3.75 i1=2.5 i2=3.75 i3=3.333333;
      all_have_means=true. `brievc check` clean. No compiler bug (one authoring
      slip: `out` is a reserved observable-boundary keyword — renamed to `dst`).
  - [ ]* 6.2 Property test — Property 8: true mean = arithmetic average
    - **Feature: recommender-app, Property 8: for any user/item with ≥1 observed
      rating, the computed mean equals the arithmetic average of the observed
      ratings and is never a degenerate constant.** min 100 iters, checked vs the
      Task 5 reference.
    - _Validates: Requirements 4.1, 4.5_
  - [x] 6.3 Key-set imputation — user side Eq. 7 and item side §3.2 (EXECUTED, not dead)
    - build the imputed key-set vectors used by PCC and prediction; observed entry
      = real rating, missing entry = the Eq. 7 / §3.2 estimate (corrects C++
      defect #2 — the loop must run).
    - _Requirements: 4.3, 4.7_
    - DESIGN DECISION (user-confirmed): two-stage similarity (reading 1). A BASE
      PCC over the RAW observed overlap drives imputation (Eq. 7 needs weights);
      the SERVED PCC (6.5) is recomputed over the imputed space. Matches the
      design DAG UMEAN→IMPUTE→SIM.
    - DONE: `cf_engine.bv`. Part 2a `base_sim_user`/`base_sim_item` — the
      oracle's mean-centered Pearson, computed SPARSELY by merging two
      item-ascending CSR runs (`overlap_acc`), O(|a|+|b|). Part 2b `impute_user`
      (Eq. 7) / `impute_item` (§3.2): observed cell ⇒ real rating; missing ⇒
      `mean + Σ basesim·(r−mean) / Σ|basesim|` over the neighbor set, falling back
      to the row/col mean when Σ|sim|==0. The user-side neighbor set is item i's
      CSR COLUMN (`item_user[item_off[i]..]`) — the item orientation drives
      user-side imputation (the payoff of the dual-orientation CSR), and vice
      versa. `lookup_user_item`/`lookup_row` find an observed rating (-1.0
      missing sentinel; early-out on the sorted row).
    - ✅ GATE MET (Property 10 — the loop EXECUTES and matches the formula):
      engine `impute_user(u3,i3)=3.16666675` == oracle
      `predict_user(u3,i3)=3.16666675` to the last digit (Eq. 7 of a single
      missing cell IS the oracle's all-neighbor prediction). `base_sim(u0,u1)=
      0.852802813` matches the oracle anchor; symmetry + self-sim=1.0 both
      orientations. `impute_differs_from_mean=true` (filled ≠ fallback mean ⇒
      loop ran, defect #2 corrected); observed cells return the real rating
      untouched; item side `impute_item(i3,u3)=3.44402552` fills + differs (the
      exact mirror of the verified user side; the full item-based Eq. 30
      exercises it in 7). `brievc check` clean. No compiler bug this increment.
  - [ ]* 6.4 Property test — Property 10: imputation executes and matches the formula
    - **Feature: recommender-app, Property 10: for any key neighborhood with
      missing entries, the imputed vector differs from the raw vector at those
      entries and each imputed entry equals the Reference_Algorithm estimate within
      tolerance.** min 100 iters.
    - _Validates: Requirements 4.3, 4.7_
  - [x] 6.5 PCC similarity: user-user Eq. 9 and item-item Eq. 10, mean-centered, `Sqrt#`
    - over the imputed key-set space; symmetric (compute once, mirror);
      zero-variance (zero norm) → similarity 0 (no NaN); NaN/Inf guard → 0.
    - _Requirements: 4.2, 4.6_
    - DESIGN DECISION (user-confirmed): the served key-set is the UNION of items
      either user rated; each entry imputed (real or Eq. 7), mean-centered by the
      user's true mean. Oracle gap closed: `reference.bv` gained a dense
      `pcc_imputed_users` (+`impute_cell_user`) as the independent `sim'` anchor.
    - DONE: `cf_engine.bv` `sim_user`/`sim_item` (`sim'`, Eq. 9/10). Sparse UNION
      merge (`sim_union_*` + `sim_next_item`/`sim_advance`/`sim_step`) over the
      two item-ascending CSR rows — processes EVERY union key (an item rated by
      one user contributes the other's Eq. 7 imputation), unlike overlap_acc's
      intersection-only walk. `pcc_finish` shared with the base stage
      (zero-variance → 0.0, the NaN/Inf guard is its da/db<=0 domain check — no
      Sqrt# of a negative, no /0).
    - ✅ GATE MET: all six user-pair sim' match the oracle's pcc_imputed_users to
      the last digit — simp(u0,u1)=0.852802813 (=base sim, no gaps in that
      union), (u0,u2)=0.707106769, (u0,u3)=0, (u1,u2)=0.301511347,
      (u1,u3)=-0.132410213, (u2,u3)=0.536745071; symmetry both orientations;
      self-sim'=1.0 user+item. The u3 pairs DIVERGE from base sim exactly where
      imputation fills i3 — confirming stage 2 runs over the imputed space, not
      the raw overlap. `brievc check` clean. No compiler bug this increment.
    - RISK-LEDGER TODO (pre-commit): inspect the optimized Sqrt#/division IR.
  - [ ]* 6.6 Property test — Property 9: PCC symmetric and bounded
    - **Feature: recommender-app, Property 9: for any user pair and item pair, the
      PCC similarity is symmetric (sim(a,b)==sim(b,a)), lies in [-1,1], and equals
      the independent reference PCC within tolerance.** min 100 iters.
    - _Validates: Requirements 4.2, 4.6_
  - Gate: means, imputed key-sets, and both PCC matrices match the Task 5 reference
    on the 4×4 example within 1e-6; property tests green; optimized IR for the
    `Sqrt#`/division kernels inspected (risk-ledger discipline).
    - ✅ GATE MET (committed 7e466a01). All 6.1/6.3/6.5 values match the oracle to
      the last digit. Sqrt#/div IR inspected (cf_engine.ll pcc_finish): Sqrt#
      lowers to `@llvm.sqrt` and the `da<=0 || db<=0` zero-variance guard
      DOMINATES the sqrt/fdiv (no Sqrt# of a negative, no div-by-zero reaches a
      served value); division is native `fdiv fast`. Property tests (6.2/6.4/6.6)
      are optional `*` sub-tasks — not implemented (per the legend, only on
      request); the 4×4 oracle anchor covers the gate.
    - ⚠ FIRST-GREEN NOTE for scale-up (Tasks 9–11): the fixture IR resolved
      `Float` to f32 (`@llvm.sqrt.f32`, `float`). Harmless at 4×4 (1e-6 met), but
      the design + tasks.md first-green decision want 64-bit Float at 943²/1682²
      scale for Sqrt#/PCC accuracy. Confirm `Float` resolves to f64 (or annotate
      Float64) when wiring the real u.data-scale engine. NOT a Task 6 defect.

- [ ] 7. CF_Engine part 2 — kNN prediction, fusion, clamp, fallbacks
  _Design: The CF Engine → kNN prediction / Fusion. Depends on Task 6._
  - [x] 7.1 Per-side kNN prediction: user Eq. 29 and item Eq. 30, k=30, η-normalized, each neighbor once
    - select the k=30 nearest by similarity; iterate the selected set straight
      through, once each (corrects C++ defect #3 — no `+first −last` walk); η = the
      similarity sum over the SAME neighbor set.
    - _Requirements: 4.4, 4.8, 4.9, 4.10, 4.11, 4.12_
    - ORACLE GAP CLOSED: prediction weights by sim' (Req 4/8/10/11 name sim'),
      but the oracle's predict_user used BASE sim (anchors imputation). Added
      `predict_user_imputed` (+`predui_acc`) to reference.bv as the sim'-weighted
      anchor; the base predict_user stays as the imputation anchor.
    - DONE: `cf_engine.bv` `predict_user`/`predict_item` (Eq. 29/30) weighted by
      `sim_user`/`sim_item` (sim'). Candidates from the CSR (item s's column /
      user a's row); `knn_aggregate`→`knn_select`→`knn_argmax` select the
      NEIGHBOR_K=30 largest sims, adding each neighbor's contribution the instant
      it is selected (defect-#3 correction is STRUCTURAL — no index walk to go
      off-by-one). η = Σ sim' over exactly the selected set. Zero-η ⇒ mean.
    - ✅ GATE MET: predui(u3,i3)=2.75732088, (u0,i0)=4.63667488, (u1,i2)=2.2247615
      all match reference.bv's predict_user_imputed within 1e-6. ⚠ DEFECT-#3
      PROOF (the 4×4 has <30 neighbors so cannot exercise truncation): a
      synthetic 32-user probe (`probe_knn_truncation`) with 31 candidates on one
      item shows probe_k30_truncates=true (η at k=30 ≠ η at k=31) and
      probe_dropped_is_min=true (the dropped neighbor is the smallest sim ⇒
      selection took the top 30, not sum-all). NOTE: f32 reassociation shifted
      simp(u1,u3)/(u2,u3) by ~1e-8 — within tolerance, the design's allowed drift.
  - [ ]* 7.2 Property test — Property 11: per-side prediction matches an independent reference
    - **Feature: recommender-app, Property 11: for any small population, r̂ᵘas (Eq.
      29) and r̂ⁱas (Eq. 30) each equal an independent reference of the respective
      equation within tolerance.** min 100 iters.
    - _Validates: Requirements 4.4, 4.8_
  - [ ]* 7.3 Property test — Property 12: each neighbor contributes exactly once
    - **Feature: recommender-app, Property 12: for any selected k-NN set, the
      multiset of contributing neighbors equals the selected set exactly — first
      not doubled, last not dropped.** min 100 iters.
    - _Validates: Requirements 4.9_
  - [ ]* 7.4 Property test — Property 13: η equals the similarity sum over the same neighbors
    - **Feature: recommender-app, Property 13: for any user-based and item-based
      prediction, η equals the sum of the similarities over exactly the neighbor
      set used in the numerator.** min 100 iters.
    - _Validates: Requirements 4.10, 4.11_
  - [x] 7.5 λ fusion (Eq. 31) + clamp to [1,5] + zero-η fallbacks
    - `r̂as = λ·r̂ᵘ + (1−λ)·r̂ⁱ`, λ default 0.5 from env; clamp [1,5]; η_u=0 → user
      mean, η_i=0 → item mean, both zero → fused means clamped.
    - _Requirements: 4.13, 4.14, 4.15, 4.16, 4.17_
    - DONE: `cf_predict(pop,m,a,s,lam)` = clamp15(lam·predict_user + (1−lam)·
      predict_item). The zero-η fallbacks live INSIDE the two predictors
      (η_u=0 ⇒ ūa, η_i=0 ⇒ t̄s), so a both-zero cell naturally fuses the two means
      and clamps (Req 4.17) with no extra branch. λ ∈ [0,1] contracted; env read
      deferred to Task 10/12 wiring (default 0.5 used here).
    - ✅ GATE MET: cf_predict(u3,i3,0.5)=3.14069247 ∈ [1,5]; fuse_matches=true (=
      manual λ-blend); lambda1_is_user & lambda0_is_item true (Property-14 shape:
      λ=1 ⇒ user side, λ=0 ⇒ item side). clamp15 edges verified in reference.bv.
  - [ ]* 7.6 Property test — Property 14: fusion is the linear λ-blend and monotonic in λ
    - **Feature: recommender-app, Property 14: for any u, i, λ∈[0,1], fused = λ·u +
      (1−λ)·i; = u at λ=1, = i at λ=0, monotonic between.** min 100 iters.
    - _Validates: Requirements 4.13_
  - [ ]* 7.7 Property test — Property 15: served prediction is clamped to [1,5]
    - **Feature: recommender-app, Property 15: for any (user,item) and population,
      the served Prediction lies in [1,5].** min 100 iters.
    - _Validates: Requirements 4.14_
  - [ ]* 7.8 Property test — Property 16: zero-η fallback uses the true mean
    - **Feature: recommender-app, Property 16: for any population, η_u=0 ⇒ r̂ᵘ=true
      User_Mean, η_i=0 ⇒ r̂ⁱ=true Item_Mean, both zero ⇒ the λ-fused means clamped
      to [1,5].** min 100 iters.
    - _Validates: Requirements 4.15, 4.16, 4.17_
  - [ ]* 7.9 Unit test: default `k = 30`
    - example test that the Neighbor_Count default is 30 (Req 4.12).
    - _Requirements: 4.12_
  - Gate: `cf_predict` on the 4×4 example matches the Task 5 reference within 1e-6
    pre-clamp; all fusion/clamp/fallback property tests green.
    - ✅ GATE MET. Prediction (sim'-weighted Eq.29/30) + fusion/clamp match the
      reference oracle within 1e-6; defect-#3 truncation proven on a 31-candidate
      probe. Property tests (7.2/7.3/7.4/7.6/7.7/7.8/7.9) are optional `*` — not
      implemented (per legend); the oracle anchors + the truncation probe cover
      Properties 11/12/13/14/15 structurally on this build. `brievc check` clean.

- [ ] 8. CF_Engine part 3 — top-N serving (exclude rated, item-ascending tie-break)
  _Design: The CF Engine → Serving; API `/recommendations`. Depends on Task 7._
  - [x] 8.1 `cf_recommend(model, user, topn)`: exclude already-rated, order desc, tie by item index asc
    - length = min(Top_N, eligible items); deterministic item-ascending tie-break.
    - _Requirements: 4.18, 4.19_
    - ORACLE GAP CLOSED (option 1, user-confirmed): the oracle gained the FULL
      item-side mirror (pcc_items/impute_cell_item/pcc_imputed_items/
      predict_item_imputed) + fused cf_predict_ref + recommend_user serving, so
      the engine's item side AND fused prediction are now value-anchored (not
      just structurally). Engine predict_item(u3,i3)=3.52406406 == oracle
      predii; cf_predict==cf_predict_ref==3.14069247.
    - DONE: `cf_engine.bv` `cf_recommend` (TOP_N=5): rec_init marks already-rated
      items (rec_rated = membership in the user's CSR row) as excluded;
      rec_fill/rec_argbest select top-N by DESCENDING cf_predict, item-ascending
      tie-break (strict `>` keeps the smaller index; items scanned ascending).
      picked[] is pre-zeroed (ivec_new memory is uninitialized).
    - ✅ GATE MET: engine rec_u3=[i3] (len 1), rec_u0=[] (rated all) — match the
      oracle's recommend_user. probe_serving (5×5, items 3&4 forced tie):
      serv_excludes_rated, serv_descending, serv_tie_3_before_4,
      serv_tie_scores_equal all true.
    - ⚠ COMPILER BUG SURFACED + FIXED (Req 9.7): the oracle's recommend_user
      exposed a raw Ptr<T> scalar index load/store CSE-alias miscompile
      (independent inttoptr per access ⇒ no provenance ⇒ -O3 LTO hoisted the
      picked[] load across the store ⇒ stale read). Isolated via a volatile-load
      .ll A/B (scratch/ptr_store_crossdefn.bv probes). Fixed on
      `fix/ptr-index-provenance` (volatile raw scalar Ptr<T> load/store + regression
      test + BUGS.md); confirmed end-to-end on integration/ptr-provenance — oracle
      now serves correctly with NO workaround. PR-ptr-index-provenance.md documents
      the rejected options + the optimization tradeoff + the provenance-threading
      successor. NOT worked around in the .bv.
  - [ ]* 8.2 Property test — Property 17: recommendations exclude already-rated items
    - **Feature: recommender-app, Property 17: for any user, no item in the served
      set is one the user already rated.** min 100 iters.
    - _Validates: Requirements 4.18_
  - [ ]* 8.3 Property test — Property 18: top-N ordering with deterministic tie-break
    - **Feature: recommender-app, Property 18: for any per-item predictions, the
      set is ordered by predicted rating desc, ties broken by item index asc, with
      length = min(Top_N, eligible).** min 100 iters.
    - _Validates: Requirements 4.19_
  - [ ]* 8.4 Property test — Property 24: interpreter-backend parity for the CF engine
    - **Feature: recommender-app, Property 24: for any small population, the
      interpreter's recommendation output equals the native-compiled backend's —
      same item ordering, scores equal within float tolerance.** min 100 iters.
    - _Validates: Requirements 8.5_
  - Gate: top-N on the 4×4 example matches the reference ordering exactly;
    exclusion + tie-break property tests green; interpreter/backend parity holds.
    - ✅ GATE MET (post fix/ptr-index-provenance). Engine serving == oracle
      recommend_user on the 4×4; exclusion + descending + item-asc tie-break
      proven on the probe_serving fixture. Property tests (8.2/8.3/8.4) are
      optional `*` — not implemented (per legend); the oracle anchor + the tie
      probe cover Properties 17/18 structurally. NOTE: the Task 8 .bv work is
      committed on the vessel (wip ec38e15f); build/run verified on
      integration/ptr-provenance (which carries the compiler fix).

- [x] 9. Similarity_Cache + refresh (atomic pointer swap, signature freshness, persistence)
  _Design: The Similarity Cache + Refresh. Depends on Tasks 6, 8. ⚠ RISK: reactor pointer-swap refresh._
  - [x] 9.1 `obj SimCache` (both matrices + both mean vectors + `PopSignature`)
    - the served snapshot the CF_Engine reads per prediction (O(k) per request).
    - _Requirements: 6.3, 10.4_
    - DONE: `cf_engine.bv` `obj SimCache` (user_sim/item_sim `Matrix`, borrowed
      user_mean/item_mean `Vector`, dims) + `simcache_build` (lower-triangle
      sim_user/sim_item once, mirrored — symmetry halves the PCC work; diagonal
      1.0 by construction) + O(1) accessors (`simcache_user_sim`/`_item_sim`/
      `_user_mean`/`_item_mean`) + `simcache_free` (frees ONLY the two owned
      matrices; the mean vectors are borrowed from `Means`, freed by means_free —
      not double-freed). The `PopSignature` field lands with 9.4 (freshness).
      ✅ GATE MET (integration/ptr-provenance debug binary): the cache is a pure
      MEMOIZATION — `simcache_user_sim(sc,a,b)` == on-the-fly `sim_user` for all
      6 off-diagonal user pairs + 3 item pairs, diagonal 1.0 both orientations,
      symmetric, borrowed means read through. No new numeric claim; the 6.5
      oracle anchor still covers the values. All Task 6/7/8 lines still green.
      The matrix reads ride the merged ptr-provenance fix. No compiler bug.
  - [x] 9.2 Compute a fresh `SimCache` off to the side + atomic pointer swap
    - new cache in fresh `Malloc#` blocks, then a one-step pointer assignment
      between poll iterations; free the old snapshot after reads drain.
    - _Requirements: 6.4, 6.5_
    - DONE: `cf_engine.bv` `obj Served { slots: IntVec }` — a control block
      holding the current snapshot's 4 Malloc# addresses + 2 dims (objs are value
      handles, not mutable cells, so the indirection lives in the control block).
      `served_new`/`served_read` (O(1) handle reconstruct, no copy)/`served_install`
      (THE swap: rewrite the slots, return the OLD handle to free AFTER reads
      drain)/`served_free`. WHY ATOMIC: single-process poll ⇒ refresh runs BETWEEN
      sweeps, no preemptive reader can see a half-rewritten block (a threaded
      backend would need a real atomic ptr/RCU — the poll model is why we don't).
      ✅ GATE MET: probe_swap over two 4×4 pops differing in one cell (u1·i0) —
      swap_serves_A, swap_pre_swap_still_A (B built off to the side is invisible),
      swap_B_differs_from_A, swap_post_swap_is_B, swap_unaffected_pair_consistent
      (whole-snapshot swap, no partial mix), swap_old_handle_intact all true. All
      prior lines still green.
    - ⚠ PARSE QUIRK (not a compiler bug): the obj field name `cell` is a reserved
      identifier (reactive "cell") — `Served { cell: ... }` parse-errors at the
      `{`. Renamed the field to `slots`. Reserved-word rejection is correct; the
      diagnostic ("expected Semicolon") could name the reserved word — noted for a
      future opportunistic errors.rs sweep, not fixed this increment.
  - [ ]* 9.3 Property test — Property 21: cache reads always observe a complete snapshot
    - **Feature: recommender-app, Property 21: for any read sequence interleaved
      with a refresh, every read returns a fully populated, self-consistent
      snapshot (old or new), never a partial one.** min 100 iters.
    - _Validates: Requirements 6.5_
  - [x] 9.4 `PopSignature` freshness (record count + backing-source mtime) + binary persistence
    - load `simlist.txt.bin` when the signature matches; mismatch ⇒ stale ⇒
      recompute + rewrite; a partial write is removed, not left as a bad cache.
    - _Requirements: 6.1, 6.2, 6.6_
    - DONE: `cf_engine.bv` `obj PopSignature { nnz; mtime }` + `pop_signature` +
      `sig_fresh` (fresh iff BOTH match; any mismatch stale — Req 6.6); `sig`
      field added to `SimCache` (+ carried in the `Served` control block).
      Binary persistence over std/os/fs.bv (`read_file`/`write_file`/`remove_file`):
      flat image = 5-word header `[magic,nusers,nitems,nnz,mtime]` + the 4 raw
      Malloc# blocks back-to-back (`Copy#` — raw bytes, no float round-trip).
      `simcache_save` (String-shaped buffer → write_file), `simcache_probe`
      (classify ABSENT/STALE/FRESH: bad magic, wrong dims, SHORT image, or
      signature mismatch ⇒ not served — Req 6.2 partial-write safety), `simcache_load`
      (Copy# blocks into FRESH owned matrices; `simcache_load_free` frees all 4,
      vs `simcache_free` which leaves the borrowed means to means_free).
      ✅ GATE MET (scratch path, NOT the shipped simlist.txt.bin): sig fresh/stale
      (mtime, nnz) + recorded; save→probe-fresh→load bit-exact (user_sim/item_sim/
      means/sig); probe STALE under bumped mtime/nnz/shape; a 3-byte truncated
      file rejected (ABSENT); cleanup ok. 16/16 lines true, all prior green.
    - COMPILER NOTES (none a bug; all correct rejections): (a) `[true][true]`
      trivial-contract rejected → omit brackets; (b) prelude makes fs.bv names
      VISIBLE but a defn is only EMITTED when the unit imports the module —
      explicit `import "std/os/fs.bv"` needed (defn-liveness rule); (c) `write_file`
      returns `Result<Int,Int>` not `Int` → unwrap. Plus the 9.2 reserved-field
      `cell` quirk. The helpful-diagnostics style handled all three well.
  - [ ]* 9.5 Property test — Property 22: cache freshness is signature equality
    - **Feature: recommender-app, Property 22: for any artifact signature and
      current-population signature, fresh iff both record count and mtime match;
      any mismatch is stale.** min 100 iters.
    - _Validates: Requirements 6.6_
  - [ ]* 9.6 Property test — Property 19: similarity is a function of the rating population
    - **Feature: recommender-app, Property 19: for any population change that
      alters a pair's overlap, the computed similarity for that pair changes
      accordingly — derived from the current population, not read from the static
      artifact as ground truth.** min 100 iters.
    - _Validates: Requirements 4.20_
  - [ ]* 9.7 Unit test: `simlist.txt` fixture comparison
    - compare the computed user-user matrix against the shipped `simlist.txt`
      within tolerance as a validation fixture (NOT ground truth) — gross-error
      catch (Req 6.7).
    - _Requirements: 6.7_
  - Gate: compute/write/load/swap round-trips; a stale signature forces recompute;
    the fixture comparison is within tolerance; the swap is observed atomic.
    - ✅ GATE MET (2026-10-20, integration/ptr-provenance debug binary;
      deliverables committed on the vessel feat/fullstack-webapp-demo). The three
      required sub-tasks (9.1/9.2/9.4) are all green on the 4×4 oracle fixture:
      the cache memoizes the engine's sim' exactly (9.1), the off-to-the-side
      build + single-step pointer swap is whole-snapshot-consistent and the old
      snapshot survives until the swap (9.2), and the signature decides freshness
      with binary save/probe/load round-tripping bit-exact (stale mtime/nnz/shape
      + truncation all rejected) (9.4). The property/unit `*` sub-tasks
      (9.3/9.5/9.6/9.7) are NOT implemented (per the legend — only on request);
      the 9.7 `simlist.txt` fixture comparison + the atomic-read Property 21 are
      the two the gate text names as `*` and are deferred with the rest. No
      compiler bug surfaced (the four parse/type/liveness stops were correct
      rejections — see 9.2/9.4 notes).

- [x] 10. u.data parser + Postgres schema + idempotent baseline bootstrap + rating upsert
  _Design: Data Models → PostgreSQL schema / Baseline bootstrap. Depends on Task 2._
  - [x] 10.1 `u.data` parser + pretty-printer, 1→0 index mapping, range filter [1,943]/[1,1682]
    - parse `user item rating timestamp`; map to 0-indexed `(user-1, item-1)`;
      discard out-of-range records and continue (never abort). Include a printer so
      the round-trip property is testable.
    - _Requirements: 2.1, 2.2, 2.3_
    - 2026-10-21: authored `examples/recommender/udata.bv` and example gate
      `scratch/udata_gate.bv`; HUMAN check/build/run passed. Strict four-field
      unsigned-decimal parsing rejects overflow, malformed fields, invalid ratings
      and out-of-range IDs per line; retains timestamps, handles CRLF and a final
      unterminated line. Printer restores one-based IDs. All six gate lines true.
      Relative import resolution exposed a compiler bug; fixed separately on
      `fix/relative-import-paths` (1508e5b0), PR submitted by human, merged into
      `integration/ptr-provenance` for continued feature work.
  - [ ]* 10.2 Property test — Property 3: u.data parser round-trip and index mapping
    - **Feature: recommender-app, Property 3: for any list of valid records
      (user∈[1,943], item∈[1,1682]), format→parse yields the same records, each at
      0-indexed (user-1,item-1).** min 100 iters.
    - _Validates: Requirements 2.1, 2.2_
  - [ ]* 10.3 Property test — Property 4: range filtering keeps exactly the in-range records
    - **Feature: recommender-app, Property 4: for any mix of in/out-of-range
      records, the loaded population is exactly the in-range ones and parsing
      completes without aborting.** min 100 iters.
    - _Validates: Requirements 2.3_
  - [x] 10.3b Create the schema (`accounts`, `ratings` with `(account_id,item_id)` PK, `load_state`)
    - via `pg.bv` DDL; the composite PK enables the rating upsert.
    - _Requirements: 1.1, 2.1, 3.5_
    - 2026-10-21: authored `examples/recommender/store.bv` DDL + transaction
      wrapper and `scratch/recommender_schema_gate.bv`. Baseline ratings have
      their own table, avoiding fake accounts/identity collisions. Pending human
      typecheck and live DB gate; PostgreSQL is not installed yet.
    - Schema native-build gate exposed generic-call literal element-type loss
      in `pg_decode_fields`. Fixed separately as 367470ac on
      `fix/generic-call-literal-types`; full suite and Int/String native probes
      passed. Integrated via e14fd2c7 on `integration/ptr-provenance`; human
      rebuilt integration compiler, checked store.bv (OK), and built the schema
      harness successfully. Live DB verification awaits PostgreSQL setup.
    - LIVE GATE PASSED 2026-10-21: PostgreSQL 12/main on 127.0.0.1:5432,
      database `briev_recommender_test`, non-admin role `briev_test`; trust rule
      scoped to that DB/role/address. Schema harness prints schema_created=true,
      schema_repeat=true, four_tables=true. Agent ran setup and native binary
      per clarified workflow; human retains cargo/brievc execution.
  - [x] 10.4 Idempotent baseline bootstrap guarded by `load_state('baseline')`
    - if not done, insert every valid record then mark done; if done, skip
      re-loading and use the persisted baseline; expose the 943 users to the engine.
    - _Requirements: 2.1, 2.4, 2.5_
    - 2026-10-21 increment 1: authored transaction/marker locking in
      `store_baseline_begin` and shared rollback/error preservation. Gate harness
      `scratch/recommender_bootstrap_guard_gate.bv` checks lock/relock, rollback
      preserving marker state, SQLSTATE preservation, and connection recovery.
      Gate passed after fixing pg_read_msg's received-buffer length metadata:
      all six checks true, SQLSTATE 22012 and "division by zero" preserved.
      File insertion and engine population loading now pass the gates below. Marker is
      never marked done by the guard alone.
    - 2026-10-21 completion: atomic 64-record batches, last-valid duplicate wins,
      done-marker skip even with missing source; full baseline has 100,000 rows,
      each independently compared with u.data. Persisted engine adapter passes
      943x1682 dimensions, both sparse orientations, exact small anchors, and
      SQL count/sum checks. Missing/incomplete/error/empty paths recover cleanly;
      late-batch rollback preserves prior incomplete rows. Durable deterministic
      gates: tests/fixtures/recommender/run.sh. Starred property work stays optional.
  - [x]* 10.5 Unit test: idempotent-load guard
    - run bootstrap twice against the test DB; the second run inserts nothing
      (example test, Req 2.5).
    - _Requirements: 2.5_
  - [x] 10.6 Rating upsert (`INSERT ... ON CONFLICT (account_id,item_id) DO UPDATE`)
    - a resubmitted rating replaces the prior value; scoped by `account_id`.
    - _Requirements: 3.5_
    - 2026-10-21: parameterized store_rating_upsert replaces rating and timestamp
      only at (account_id,item_id); native gates pass account/item isolation,
      missing-account FK rejection, all bounds, and caller-owned rollback.
  - [ ]* 10.7 Property test — Property 6: rating upsert replaces the prior value
    - **Feature: recommender-app, Property 6: for any account/item and valid r1
      then r2, exactly one stored rating remains for (account,item) with value
      r2.** min 100 iters.
    - _Validates: Requirements 3.5_
  - Gate: the parser round-trips and filters correctly; the schema creates; a
    double bootstrap is idempotent; an upsert replaces in place against the test DB.

- [x] 11. Account_Service over `pg.bv` (register / login / state, with isolation)
  _Design: Components → Account_Service. Depends on Tasks 2, 10._
  - [x] 11.1 `register`: validate non-empty username+password, reject duplicate, FNV-1a store, insert
    - reject empty/whitespace username or password (validation error); reject an
      already-registered username (account-exists); otherwise insert and return the
      account. Non-salted FNV-1a hash, documented as providing NO real security
      (demo).
    - _Requirements: 1.1, 1.2, 1.3_
  - [x]* 11.2 Property test — Property 1: credential validation rejects empty inputs
    - **Feature: recommender-app, Property 1: for any username/password, register
      validation rejects iff username or password is empty/whitespace-only, accepts
      otherwise.** min 100 iters.
    - _Validates: Requirements 1.3_
  - [x]* 11.3 Unit tests: duplicate-username rejection + login success/failure
    - example tests for Req 1.2 (account-exists), 1.4 (login success), 1.5
      (auth-failed).
    - _Requirements: 1.2, 1.4, 1.5_
  - [x] 11.4 `login` (username+password match → session) and `account_state` (own data only)
    - auth-failed on no-match; `account_state` filters every query by `account_id`.
    - _Requirements: 1.4, 1.5, 1.6_
  - [x]* 11.5 Property test — Property 2: account state isolation
    - **Feature: recommender-app, Property 2: for any accounts and ratings, an
      account-state query for A returns only rows with account_id = A, never
      another account's data.** min 100 iters.
    - _Validates: Requirements 1.6_
    - 2026-10-21: native run_accounts.sh passes 144 credential combinations, Unicode
      whitespace, FNV vectors, atomic duplicates, successful/failed login and explicit
      kernel-random session ownership. account_state token-authenticates a single
      owner-filtered query; 120 generated isolation cases plus empty/deleted accounts,
      forged/restarted sessions and SQL-error recovery pass. Human confirmed task 12
      composes recommendations for the same owner. Build/Praetor pass; full library
      suite: 3164 passed, 38 known failures, no new failure names.
  - Gate: register/login/state run against the test DB; validation, duplicate, and
    isolation property/unit tests green.

- [x] 12. Backend server — poll event loop, connection lifecycle, HTTP routing, Live_Channel
  _Design: Components → Backend server; Concurrency Model; API Surface. ⚠ RISK: reactor + many sockets. Depends on Tasks 1, 3, 8, 9, 10, 11._
  - [x] 12.1 Reactor skeleton: listener + poll set + connection table (per-fd state)
    - single-process `SYS_POLL` sweep; each ready fd advances its own state
      machine; connection table keyed by fd (parse state, account_id, upgraded?,
      owner). No `main()` — the reactor is the scheduler.
    - _Requirements: 10.3, 8.1_
    - 2026-10-21: reactor.bv provides a nonblocking listener, stable bounded
      connection slots, poll sweep, fd lookup and owned cleanup. Native
      reactor_gate.bv passes acceptance, queued-peer capacity, nonblocking flags,
      readiness isolation, cleared ownership on reuse, removal and bad config.
      brievc check and directory Praetor pass. HTTP lifecycle starts at 12.2;
      this gate makes no 1000-channel performance claim. See architecture
      applications/recommender-reactor.md for ABI and ownership rules.
  - [x] 12.2 Connection lifecycle: accept → read request → dispatch → write (partial-write loop) → close/EOF
    - _Requirements: 10.3_
  - [x] 12.3 HTTP routing to Account_Service and CF_Engine (the API table)
    - `POST /register`, `POST /login`, `GET /movies`, `POST /rating` (reject rating
      ∉[1,5]), `GET /recommendations` (cold-start gate <5 ratings), `GET /state`
      (own only), `POST /admin/refresh`. Resolve the account from the session token
      and scope all data to it.
    - _Requirements: 1.1, 1.4, 1.6, 3.1, 3.2, 3.3, 3.4, 6.4_
  - [x]* 12.4 Property test — Property 5: rating-value validation
    - **Feature: recommender-app, Property 5: for any integer rating value, a
      submission is accepted iff the value is within 1..5 inclusive.** min 100
      iters.
    - _Validates: Requirements 3.4_
  - [x]* 12.5 Property test — Property 7: rating threshold gates recommendations
    - **Feature: recommender-app, Property 7: for any user, the serve decision is
      cold-start when <5 ratings and serves a Recommendation_Set when ≥5
      ratings.** min 100 iters.
    - _Validates: Requirements 3.1, 3.3_
  - [x] 12.6 Websocket upgrade route + Live_Channel: tag connection with owning account_id
    - a `GET /live?token=…` upgrade transitions the connection to `WebSocket` state
      and records its owner.
    - _Requirements: 5.1_
  - [x] 12.7 Rating-over-Live_Channel → persist → recompute (if ≥5) → push on the OWNING channel only
    - decode the client frame, persist the rating, recompute the owner's rec-set
      from the served cache, encode a server frame to that account's channel only —
      never broadcast.
    - _Requirements: 5.2, 5.5, 3.2_
  - [x]* 12.8 Property test — Property 20: live push is delivered only to the owning account
    - **Feature: recommender-app, Property 20: for any set of connected accounts, a
      rec-set generated for A's rating is delivered only to A's channel(s), never
      another account's.** min 100 iters.
    - _Validates: Requirements 5.5_
  - [x]* 12.9 Integration test: end-to-end register → rate ×5 → live rec-set over loopback
    - the fetch path over loopback → backend → test PG → back; cross the threshold
      and receive a Recommendation_Set over the Live_Channel.
    - _Requirements: 5.1, 5.2, 3.3_
  - 2026-10-21: all task-12 native API/socket/WebSocket gates pass, including
    partial writes, owner-only push, five-rating threshold and refresh. Three
    proptest properties run 128 native cases each. Compiler fixes are isolated
    for collection rebinding and Float Abs overload names; JSON parser grammar
    and progress are repaired in stdlib. No interpreter changes, as requested.
    Final verification and known baseline failures are recorded in
    docs/plans/2026-10-21-recommender-server.md. Commits await workflow approval.
  - Gate: the server accepts, routes every API-table endpoint, gates cold-start,
    upgrades to websocket, and pushes a rec-set to the correct owner only; the
    end-to-end path returns a rec-set after 5 ratings.

- [x] 13. Checkpoint — full backend + net stack green
  - Ensure all tests pass, ask the user if questions arise. Confirm Tasks 1–12
    gates hold together (net stack + CF engine + cache + server), `cargo test
    --lib` green, Praetor clean on changed directories, and every surfaced compiler
    bug is fixed-with-regression and logged in `BUGS.md`.

  - 2026-10-21: completed on integration/ptr-provenance. All required native
    net-stack/CF/cache/bootstrap/account/server gates pass together; library
    suite 3169 passed, exactly the 38 environment failures accepted by the human.
    No environment-failure fixes or optional unfinished tasks included. Build
    passes without Rust warnings; app/fixture/stdlib Praetor clean, LLVM retains
    its documented diagnostics. Quick IR determinism passes; full corpus has
    six identical programs and the known giantnode admission rejection. Evidence:
    docs/plans/2026-10-21-backend-checkpoint.md. Task 14 remains unstarted.

- [x] 14. Frontend — extend `glue/web.js` + `web/fetch.bv`, then the `.rbv` app
  _Design: Frontend web client extension; Data path (Browser). ⚠ RISK: frgn glue. Depends on Task 12._
  - [x] 14.1 Glue: `fetch_method(url, method, body, content_type)` + websocket client (`ws_open`/`ws_send`/`ws_onmessage`)
    - extend `glue/web/web.js` and `src/glue/web_generator.rs` wrapping browser
      `fetch`/`WebSocket`.
    - _Requirements: 9.6, 8.3_
  - [x] 14.2 `lib/std/web/fetch.bv`: `http_get`/`http_post`/`http_put`/`http_delete` + a websocket wrapper
    - over `fetch_method` (method+body+content type), keeping the existing bare
      `fetch` GET; a thin Briev wrapper over the glue websocket for the Live_Channel.
    - _Requirements: 9.6, 5.1_
  - [x] 14.3 The `.rbv` app: register / rate / cold-start gating / live recommendations, using `json.bv`
    - UI flows: register+login, present movies to rate while <5 ratings and NOT a
      rec-set, submit ratings, open the Live_Channel, display the most-recent
      received rec-set, reconnect on unexpected close.
    - _Requirements: 1.1, 3.1, 3.2, 5.1, 5.3, 5.4, 8.3_
  - [ ]* 14.4 Integration test: an `.rbv` page POSTs JSON and renders the reply; opens the Live_Channel and renders a pushed rec-set
    - over loopback against the Task 12 backend.
    - _Requirements: 9.6, 5.3_
  - Gate: the frontend registers, rates, is gated at cold-start, opens the
    Live_Channel, and renders live recommendations against the running backend.

- [ ] 15. Load_Simulator (N accounts, poll-multiplexed concurrent clients, failure-tolerant accounting)
  _Design: Concurrency Model → Load_Simulator. Depends on Task 12._
  - [ ] 15.1 Register N accounts against the backend
    - _Requirements: 7.1_
  - [ ] 15.2 One process, a `poll` set over N client sockets, a concurrent Live_Channel per user
    - same multiplexing approach as the server — no threads.
    - _Requirements: 7.2_
  - [ ] 15.3 Stream rating submissions from each simulated user
    - _Requirements: 7.3_
  - [ ] 15.4 Run accounting + failure tolerance
    - report ratings submitted and Recommendation_Sets received; on a channel
      failure, record it and continue with the remaining users.
    - _Requirements: 7.4, 7.5_
  - [ ]* 15.5 Integration test: simulator run accounting
    - a small-N run reports the expected counts and survives an injected channel
      failure (continues the run).
    - _Requirements: 7.4, 7.5_
  - Gate: an N-user run registers, opens N channels, streams ratings, reports
    accurate counts, and tolerates a channel failure.

- [ ] 16. Performance verification (4× bound, live-update latency, concurrency bound)
  _Design: Performance Design. ⚠ RISK: float kernels — verify optimized IR. Depends on Tasks 8, 9, 12, 15._
  - [ ] 16.1 Benchmark harness entry: prediction-phase throughput vs the C++ baseline
    - use `bash benchmarks/build_and_bench.sh` (never ad-hoc timing); measure
      per-prediction throughput of the Briev engine and the C++ baseline on
      `u.data`; confirm Briev ≤ 4× the baseline. This compares runtime only, not
      behavior (the engine does not reproduce the C++ defects).
    - _Requirements: 10.1_
  - [ ]* 16.2 Measurement test: live-update latency ≤ 50 ms
    - over an open Live_Channel on the bootstrap population, assert the rec-set is
      sent within 50 ms of the rating.
    - _Requirements: 10.2_
  - [ ]* 16.3 Measurement test: 1,000 concurrent Live_Channels without valid-request rejection
    - drive the simulator to 1,000 channels and confirm no valid request is
      rejected for resource exhaustion; confirm per-request cost reads the cache
      and does not scale with population size.
    - _Requirements: 10.3, 10.4_
  - Gate: the prediction phase is within 4× the C++ baseline; live-update latency
    and the 1,000-channel bound hold; the float kernels' optimized IR was inspected.

- [ ] 17. Final checkpoint — the whole system green
  - Ensure all tests pass, ask the user if questions arise. Confirm every
    requirement clause is covered, all 24 property tests + the unit/integration
    tests are green, the architecture doc(s) touched by structural changes were
    updated in the same commit, every surfaced compiler bug is fixed-with-regression
    and logged in `BUGS.md`, and Praetor is clean on changed directories.

## Notes

- Tasks marked `*` are optional test sub-tasks and can be skipped for a faster
  first-green MVP; the model must NOT implement them unless asked. Top-level tasks
  are never optional.
- Each task references the specific requirement clauses it implements for
  traceability; the 24 property tests each cite the design property and the
  requirement it validates.
- The layer-cake order (sockets → PG → HTTP/WS → CF engine → cache →
  parser/schema → account service → server → frontend → simulator → perf) makes
  every layer testable before the next depends on it — no big-bang integration.
- Correctness for the CF engine is checked against the **independent reference**
  (Task 5), NOT `recommender_singlepass.cpp`.
- **Compiler-bug discipline is cross-cutting** (see the START HERE rule): any bug
  surfaced is reproduced minimally, fixed on the compiler side with a regression
  test on its own `fix/` branch from main, and logged in `BUGS.md` — never worked
  around in the stdlib. Tasks carrying `⚠ RISK` touch the design's named
  highest-risk areas; keep each minimal `.bv` repro under test as a regression guard.
- Follow WORKFLOW.md's teaching cadence: one sub-step, explain (what/how/why),
  verify the gate, tick the box with a one-line note, then move on.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4", "4.1", "4.2", "10.1"] },
    { "id": 1, "tasks": ["1.5", "1.6", "1.7", "4.3", "5.1", "5.2", "10.2", "10.3"] },
    { "id": 2, "tasks": ["2.1", "2.2", "2.3", "2.4", "3.1", "3.2", "6.1", "6.3"] },
    { "id": 3, "tasks": ["2.5", "2.6", "3.3", "3.5", "3.6", "6.2", "6.4", "6.5"] },
    { "id": 4, "tasks": ["2.7", "2.8", "3.4", "3.7", "3.8", "6.6", "7.1"] },
    { "id": 5, "tasks": ["2.9", "7.2", "7.3", "7.4", "7.5", "7.9"] },
    { "id": 6, "tasks": ["7.6", "7.7", "7.8", "8.1"] },
    { "id": 7, "tasks": ["8.2", "8.3", "8.4", "9.1", "9.2", "9.4"] },
    { "id": 8, "tasks": ["9.3", "9.5", "9.6", "9.7", "10.3b"] },
    { "id": 9, "tasks": ["10.4", "10.6", "11.1", "11.4"] },
    { "id": 10, "tasks": ["10.5", "10.7", "11.2", "11.3", "11.5"] },
    { "id": 11, "tasks": ["12.1", "12.2", "12.3", "12.6"] },
    { "id": 12, "tasks": ["12.4", "12.5", "12.7"] },
    { "id": 13, "tasks": ["12.8", "12.9", "14.1"] },
    { "id": 14, "tasks": ["14.2", "15.1", "15.2"] },
    { "id": 15, "tasks": ["14.3", "15.3", "15.4"] },
    { "id": 16, "tasks": ["14.4", "15.5", "16.1"] },
    { "id": 17, "tasks": ["16.2", "16.3"] }
  ]
}
```

Task 10 PR handoff (2026-10-21): integration feature commit 758f1d95; clean feature
branch feat/recommender-persistence at 19be337d (main-based, no compiler/stdlib
fix commits). Stdlib PR branches: fix/pg-receive-length at db77a61b, based on the
published feat/net-db-postgres because main lacks pg.bv; fix/result-wrong-side-unwrap
at dac3aa4a, main-based and dependent on compiler 23cbbdac. All three pushed to
fork. PR bodies: PR-pg-receive-length.md, PR-result-wrong-side-unwrap.md, and
PR-recommender-persistence.md. Feature requires the earlier PostgreSQL and
rating_population feature PRs plus both stdlib fixes; integration remains the
verified execution surface. Post-carve native corpus passes; WORKFLOW.md unchanged.
Task 11 PR handoff (2026-10-21): committed on integration as 2345b932; clean
main-based feature branch feat/recommender-accounts at ad6aea3e, pushed to fork.
PR body: PR-recommender-accounts.md. Depends on Task 10 and its stdlib/compiler
prerequisites. Verified integration checkout retained; WORKFLOW.md unchanged.

Task 14 required browser gate passed 2026-10-22: native backend + Chrome; registration/login, duplicate/distinct ratings, cold-start, latest live updates, reconnect/state restore, logout and 375px layout. Optional 14.4 intentionally skipped. Cache changes preserve the direct equations, persist versioned/revisioned snapshots, and refresh off the reactor; exact-reference and failure lifecycle gates pass. Final compiler-suite and branch handoff evidence follows in the tracked plans.

Final handoff (2026-10-22): integration commits 2f5ad2bf (compiler), 892dcd6c (stdlib), 7aa26f2c (cache), 6fb27e01 (frontend). Pushed and verified fork refs: fix/wasm32-web-runtime 9680e5f8; feat/portable-web-stdlib 8e6c8be1; feat/recommender-cache 25a80f2b; feat/recommender-frontend e656e684. App-only branch diff against main contains zero src/ or lib/ files. Library 3178 passed / exactly 38 accepted failures. Release build, native cache/server gates, browser gates and quick determinism pass. Full corpus/harness limitations are recorded in the plans and all-41-entry ledger. Root PR-body drafts prepared. Optional 14.4 skipped. Frontend localhost:8081, backend 8080, PostgreSQL 5432 left running; temporary mini backend stopped. Main/integration were not pushed, per workflow.

## 2026-11-01 compiler closure increment

- [~] Build external recommender browser app after upstream integration.
  Minimal nested-object enum repro reproduces RatingSaved payload capacity panic.
  Prepared shared-size planner fix and regression cases; human rebuild pending.
  Library tests remain the final gate, per the human instruction.

### 2026-11-01 closure acceptance

- [x] Native/WASM build and compiler failure closure; five general layout/lifetime fixes.
- [x] Selection smoke: local visible-page updates, no transport request.
- [x] Real-server browser: register, login, select, submit rating, saved confirmation.
- [x] Pending-peer browser regressions.
- [~] Compiler library suite, run last per workflow (in progress).

## 2026-11-04 collector prerequisite increment

- [~] Close nested environment macro expansion using the shared exhaustive AST
  visitor; focused regression and native verification in progress. The existing
  load plan is in the external app repository at
  `docs/plans/2026-11-03-briev-native-load-harness.md`. General reclamation is
  still open; see `docs/plans/2026-11-04-collector-reclamation-closure.md`.

- [x] Nested environment expansion: three unit regressions and native runtime
  fixture pass; 3,441 library tests pass with delegated conformance excluded;
  build and quick IR determinism pass. No commit pending workflow approval.
  General collector allocation reclamation remains open.

## 2026-11-04 collector memory closure

- [x] Derive allocation/alias/escape proofs and consume them with native call
  regions; preserve returned, borrowed/static and caller-owned values.
- [x] Validate explicit free/realloc and allocation failure, recursion, nested
  enums, early exits and bounded repeated sampling under native memory checks.
- [x] All nine Valgrind cases: zero definite/indirect loss and zero errors.
- [x] Two 5,000-sample 500-Hz runs: RSS flat after warmup (355 and 378 pages),
  virtual memory 3,989,504 bytes constant; CSV/schema/identity/time gates pass.
- [x] Library: 3,459 pass, only delegated source sweep excluded; native and
  wasm gates, compiler build and full seven-program IR determinism pass.
- [x] Update leak report, ownership docs, BUGS, compiler closure plan and app
  load plan. Kani's executor glibc limitation is recorded, without proof claims.
- [ ] Commit/carve-out after workflow approval; no commit or push made.

Load plan: `C:/Users/wotto/code/recommender-app/docs/plans/2026-11-03-briev-native-load-harness.md`.
The collector memory blocker is closed; network journeys and capacity/endurance
campaigns remain separate delivery work.

## 2026-11-05 — completed collector checkpoint

- [x] Functional/accounting/schema gates, ten Valgrind cases and two independent
  5000-sample preflights pass; memory is flat after warmup.
- [x] App commit `80aae72` adds the repeatable checkpoint command, validator,
  corruption gates, provenance and results record.
- [x] Clean main carve-outs published: descriptor fix PR #63 (`6850858a`) and
  measurement primitives PR #64 (`c403e943`). User authorized PR creation without
  the workflow's separate human approval step.
- Verified compiler/stdlib integration: `68e81bf1`, branch
  `integration/load-collector-verified`, worktree
  `C:/Users/wotto/code/recommender-compiler-carveouts/load-collector-prerequisites`.
- Next checkpoint: controlled client transport, then one real user journey.
  The pending tuple probe remains unchanged; no workaround or capacity claim.
- Details: `C:/Users/wotto/code/recommender-app/docs/plans/2026-11-05-collector-checkpoint.md`.

## 2026-11-05 transport continuation

Controlled transport now passes partial send/read, EAGAIN, split binary bytes,
readable hangup/EOF, EPIPE without SIGPIPE, TCP success/refusal, poll cleanup and
11 invalid-bound/lifetime gates. All four successful probes pass Valgrind and
leave no newly opened descriptors. The probe now retains put_u8's returned
ByteBuf view. Collector regression readiness remains green.

Compiler fix fix/tuple-value-types (05d8aef7), PR #65:
https://github.com/Randozart/briev-lang/pull/65.
Clean lifetime-proof and stdlib transport carve-outs are undergoing final gates.
The original dirty compiler checkout is preserved. Local/fork main were
fast-forwarded to upstream 2d9d37b7; validation branches pin base 84f37578.

## 2026-11-05 — scheduled catalogue HTTP checkpoint complete

- App commit `bfa4cc3` implements bounded fresh-connection GET /movies arrivals,
  independent JSON validation, deadlines, outcome accounting and latency CSV.
- Final smoke: 25 offered at 5/s, four slots, 2s timeout, 1682 items; 25 success,
  zero misses/failures. Existing server binary c7b88cac was used; a fresh full
  server compilation did not complete. No capacity/endurance claim.
- Controlled full/split/truncated/duplicate-length/non-200/wrong-ID/stall/refusal
  and saturation gates pass. Both 50-request Valgrind cases have zero errors,
  zero lost bytes and no open network descriptors.
- Clean main-based PRs: #68 structured lifetimes (`632f602e`), #69 statement-match
  fallthrough (`bb69d282`), #70 single field-receiver evaluation (`3fb01c97`),
  #71 response framing (`400952a2`). URLs: https://github.com/Randozart/briev-lang/pull/68,
  /pull/69, /pull/70, /pull/71 on the same repository.
- Integration `fd52b03f`, branch `integration/http-load-final`, clean worktree
  `../recommender-compiler-carveouts/load-http-final`; no integration PR.
  Pinned compiler: `/home/otto/briev-load-tools/http-load-brievc-final`, SHA-256
  b9866394672f37f1a3f3e0fd74c3625362945f9fa1d0c4d35262b95dbcaad7b7.
- Final compiler gates: 3511 library tests, 10 integration tests, ten-program IR
  determinism, no build warnings or new Praetor diagnostics. Clang 17/18 execute
  all three matrix programs with identical semantic output; raw parity fails
  only on labelled elapsed-time values. Source sweep remains delegated to CI;
  Kani cannot start on this WSL glibc.
- Compiler bug discriminators: a returning final match arm suppressed earlier
  continuing arms; `factory().field` called the factory twice; plain bindings,
  literal constants, slices, enum payloads and implicit cast dependencies lost
  or conflated ownership facts. General compiler fixes replace all workarounds.
- Usage and complete evidence: `../recommender-app/benchmarks/load/HTTP-LOAD.md`
  and `../recommender-app/docs/plans/2026-11-05-http-load-checkpoint-results.md`.
- Next: authenticated rating/save/recommendation journey, then staged capacity
  and endurance work. Existing dirty compiler/app edits remain preserved.

The prior load-transport-verified worktree is now on integration/http-load-journey with the exploratory working copy. Use the clean load-http-final worktree above for reproducible builds.

## 2026-11-05 — PR #70 CI integration closed

Upstream 78be8eb6 added a HIR Field caller using the old field-loader argument.
PR #70's merged build therefore failed E0308 despite the earlier-base local
checks. Merged current upstream and pushed 22ce21eb on
fix/field-receiver-evaluation: the unevaluated HIR receiver passes None;
the already evaluated AST receiver keeps Some. All three callers were audited.
The native counter regression now runs with HIR unset/enabled at O0/O3; the
older unfixed transport compiler fails its first assertion (exit 1), while the
fixed compiler passes. Local 3499-library-test, build/check, Praetor, ten-case
IR determinism and eight-case HIR A/B gates pass. Clang 17/18 semantic parity
passes with the existing labelled-timing raw-comparator limitation.
Full replacement CI PASSED on 22ce21eb:
https://github.com/Randozart/briev-lang/actions/runs/42030028017.
PR: https://github.com/Randozart/briev-lang/pull/70.
The existing HTTP benchmark integration/binary pin remains unchanged.

## 2026-11-06 — authenticated journey complete; Linux migration handoff

Five serial authenticated ratings now pass admission/save/fresh-prediction checks,
including cold-start transition, logout and exact durable SQL receipt verification.
App implementation b3e046f; compiler integration 0adcbba2 on
integration/load-journey-verified. Main/local/fork synchronized to b9933004.
Compiler fixes: upstream PRs #72 (integer representations), #73 (entropy borrowing),
#74 (trait-default effects), #75 (tuple-field provenance). All isolated suites and
3,516 combined library tests pass; builds have no warnings. Native AST/HIR O0/O3,
ten-case determinism, eight-case AST/HIR parity and Praetor checks pass. Clang
17/18 semantic parity passes; raw matrix comparator differs only on labelled
timings. Kani cannot start on old WSL glibc. CI status must be checked on GitHub.
Final client Valgrind: zero errors/lost bytes and no open network sockets.

For a fresh agent, use the recommender repository's docs/agent/START-HERE.md,
benchmarks/load/JOURNEY.md and the dated checkpoint results. The next checkpoint
is multi-user scheduled authenticated journeys plus stage histograms, then
capacity/endurance. The legacy dirty compiler root and older worktrees are
migration snapshots, not the verified compiler. The Linux handoff supersedes
Windows absolute paths in this historical ledger.
