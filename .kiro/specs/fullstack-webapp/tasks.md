# Tasks: Full-stack Task Board + Briev net stack

## Regression closure — 2026-11-03

- PR #55: `fix/concrete-bit-cast-widths`, commit `89ed2c8d`, based on
  upstream `373e548e`; focused constructor-width regression passed.
- PR #56: `fix/guarded-tail-return`, commit `f30520c7`, based on the same
  upstream commit; focused tail-return regression passed.
- Both PR bodies contain the prepared document text. Local conformance sweep
  cancelled at the user's request; upstream CI owns that verification.

- Restored the raw Bit encoding edge while preserving Data handle casts;
  concrete Bits casts now convert pointers and correctly widen integers.
- Reconciled the tuple test with upstream's target-width handle ABI.
- Native cast reproduction and browser cast/tuple fixture pass; final library
  verification is recorded in docs/plans/2026-11-03-cast-and-tuple-regressions.md.

## Compiler fix branches — 2026-11-02

All five branches are cut from fork/main b85f953d and pushed to fork. PR body documents are untracked root artifacts. Merge callable-transaction-emission before browser-transaction-publication. Keep all distinct tests and BUGS entries when resolving append conflicts.

- `fix/enum-object-layout` — `90e71eeb`; PR body: `PR-enum-object-layout.md`.
- `fix/enum-field-constructor-context` — `6a09f605`; PR body: `PR-enum-field-constructor-context.md`.
- `fix/enum-object-projection-lifetime` — `9c4b77c6`; PR body: `PR-enum-object-projection-lifetime.md`.
- `fix/callable-transaction-emission` — `f1d79cf1`; PR body: `PR-callable-transaction-emission.md`.
- `fix/browser-transaction-publication` — `e7dec709`; PR body: `PR-browser-transaction-publication.md`.

Final gates: every isolated branch passed its focused regressions; Praetor comparison found no new diagnostics. Full suites reported only the accepted SPIR-V environment failures after addressing a CRLF-sensitive adapters.dbvl checkout issue. The first three suites recorded that conformance failure; LF normalization (no Git content diff) and targeted brievc checks passed. The final two suites passed conformance. No app changes were included in these branches.


# START HERE (fresh-session orientation — updated 2026-10-15)

Read WORKFLOW.md first (environment + the branch/PR integration flow), then this
block, then the detailed Progress log at the bottom only if you need the history.

## State of the work
- Task 0 (toolchain), Task 1 (S1 bytes.bv) — DONE.
- Design D (ByteSink trait: fixed ByteBuf + growing GrowBuf sharing derived
  writers) — DONE and verified by running. See DESIGN-D-sinks.md (now marked
  COMPLETE) and the Progress log below.
- NEXT: Task 2 — S2 lib/std/net/socket.bv (TCP over raw SysCall#). Nothing from
  Task 2 onward has started.

## Live branch map (what exists, what it's for)
- `feat/fullstack-webapp-demo` — the long-lived VESSEL for stdlib work. Has
  D1+D2+D3-WIP. The clean history lands on main via focused PRs (below), then
  this branch picks the fixes up via main. (Carries a D3-WIP commit that only
  builds once the two fixes below are on main.)
- `feat/net-bytes-sink-trait` — PUSHED TO FORK. The clean Design-D stdlib PR
  (bytes.bv + example + tier1 test + plan). PR body: PR-net-bytes-sink-trait.md.
- `fix/liveness-member-name-collision` — PUSHED TO FORK. Compiler fix. PR body:
  PR-liveness-member-collision.md.
- `fix/needs-state-type-dependent-members` — PUSHED TO FORK. Compiler fix. PR
  body: PR-needs-state-type-dependent-members.md.
- `feat/d-sinks-integration`, `integration/both-fixes` — TEMP integration
  branches (vessel/work + the two fixes merged) used to build+verify D end-to-end.
  NOT PR'd. Safe to delete once the three PRs land on main.

## PENDING ON THE HUMAN (blocks the clean close-out, NOT new stdlib work)
Open + merge three PRs on the fork, IN THIS ORDER (feature needs both fixes to
build): (1) fix/liveness-member-name-collision, (2) fix/needs-state-type-dependent-
members, (3) feat/net-bytes-sink-trait. Each PR-*.md at the repo root is the body.
After they land on main: merge main into feat/fullstack-webapp-demo (fixes arrive
the proper way), then the vessel is clean for Task 2.

## How to pick up Task 2 (socket.bv)
Follow WORKFLOW.md: work on the vessel (or an integration branch if a NEW compiler
bug appears), carve the finished socket.bv into its own `feat/net-socket` branch
from main, PR-and-doc it. Prereq: confirm the three Design-D PRs merged (so main
has the two compiler fixes GrowBuf/future stateful stdlib relies on). Build the
compiler fresh (CARGO_TARGET_DIR=~/briev-target cargo build) and re-run the
Design-D gate (tests/tier1/byte_sink_trait_smoke.bv golden = 18527210501852721050)
to confirm your binary carries the fixes before starting new work.

---

Read WORKFLOW.md first. These tasks are intentionally SMALL and TEACHING-ORIENTED.
Each has a learning goal. Do one sub-step, explain it, verify it, then move on.
Do NOT batch many sub-steps silently. Tick boxes and add notes as you go.

Legend: [ ] todo   [~] in progress   [x] done. Each task lists a concrete gate.

## Task 0 - Toolchain bring-up and first compile (prove the loop works)

Learning goal: understand how brievc is invoked, how it finds the stdlib, and how
the Windows-source / WSL-compile loop works end to end on a trivial program.

- [x] 0.1 Confirm the WSL brievc runs: print its version/help.
- [x] 0.2 Compile the existing examples/hello-world from the Windows tree with the
          WSL brievc, pointing at /mnt/c/... Capture the exact working command
          (stdlib path, --out, resource root) and record it in the Commands
          section below. This is the single most important unblock.
- [x] 0.3 Run the produced binary; confirm observable output.
- [x] 0.4 Write the pinned commands into the Commands section so every later task
          reuses them.
Gate: hello-world compiles from /mnt/c and runs; commands are written down.

## Task 1 - S1: lib/std/net/bytes.bv (the byte buffer)

Learning goal: raw memory in Briev (Alloc#/Load#/Store#), big-endian byte order,
and why wire protocols cannot use String. Pointers-as-Int, obj with mutable fields.

- [x] 1.1 Prereq check: does bits.bv expose shift/and/or on Int? Read it; if the
          ops we need are missing, note them (do not fix yet - decide with human).
- [x] 1.2 Define obj ByteBuf and buf_new/buf_free. Explain the layout (ptr,len,cap)
          and how Alloc# returns a pointer we hold as Int.
- [x] 1.3 put_u8 + get_u8 with bounds contracts. Teaching: one byte, Store#/Load#
          with a size argument, and what the [off >= 0][off < len] contract buys.
- [x] 1.4 put_u16_be/get_u16_be then put_u32_be/get_u32_be. Teaching: big-endian -
          most significant byte first - and WHY networks use it. Show the masking.
- [x] 1.5 put_bytes + put_cstr (bytes then NUL). Teaching: the String->bytes edge.
- [x] 1.6 Growth: cap doubling in put_* when len would exceed cap. DONE via
          design D's GrowBuf (grow_to_fit: Malloc# double-or-enough, Copy#, Free#,
          new ptr). The FIXED ByteBuf keeps the room precondition; GROWING GrowBuf
          reallocates. See DESIGN-D-sinks.md.
- [x] 1.7 Behavioral test harness: round-trip each width, assert equality. DONE:
          tests/tier1/byte_sink_trait_smoke.bv (golden in daily_use_smoke.rs) +
          examples/net-bytes-sink.bv. Round-trips u16-BE + cstr on both sinks.
Gate: a .bv test writes u8/u16/u32 BE and reads them back identical; brievc check
clean; any bits.bv gap and any compiler oddity logged.

## Task 2 - S2: lib/std/net/socket.bv (TCP over raw syscalls)

Learning goal: what a socket actually IS at the syscall level, the sockaddr_in
struct, byte order in network addresses, and blocking read/write loops.

- [ ] 2.1 socket() syscall (nr 41): create an fd. Teaching: AF_INET=2,
          SOCK_STREAM=1, the fd return convention, negative = -errno.
- [ ] 2.2 Build sockaddr_in in memory (16 bytes). Teaching: family LE, port BE,
          addr BE, padding - draw the byte layout explicitly.
- [ ] 2.3 tcp_connect: connect() (nr 42) to 127.0.0.1:PORT. Teaching: pointer +
          length ABI for passing a struct to the kernel.
- [ ] 2.4 sock_send/sock_recv (write 1 / read 0). Teaching: partial reads/writes,
          why a loop is mandatory, EOF (0) vs error (<0).
- [ ] 2.5 First network proof: connect to the Postgres TCP port (it accepts even
          before we speak the protocol) and confirm connect succeeds. If no PG
          yet, defer to Task 3 setup.
- [ ] 2.6 Server side (for the HTTP backend later): tcp_listen (socket+bind 49+
          listen 50) and tcp_accept (43). Teaching: the listen backlog, accept
          returning a NEW fd per connection.
Gate: tcp_connect to 127.0.0.1 returns a valid fd and send/recv moves bytes;
tcp_listen+accept round-trips a byte locally. Oddities logged.

## Task 3 - S3: lib/std/db/pg.bv (PostgreSQL wire client) - the big one

Learning goal: a real binary wire protocol - message framing (type byte + length +
payload), request/response state machines, auth, and parsing variable row sets.
Set up a local Postgres (trust/md5 auth) BEFORE coding; record how in Commands.

- [ ] 3.0 Environment: a Postgres running on 127.0.0.1:5432 with trust or md5 auth
          and a tasks DB + table. Document the exact setup steps (apt/pg_hba).
- [ ] 3.1 StartupMessage encode (protocol 3.0, user+database as NUL pairs).
          Teaching: the one message with NO type byte, length-prefixed.
- [ ] 3.2 Read one backend message: 1 type byte + Int32 length + payload.
          Teaching: the universal framing; read exactly length-4 more bytes.
- [ ] 3.3 Auth handshake: handle AuthenticationOk (R,0). If md5 required, implement
          md5(md5(pass+user)+salt) - teaching: challenge-response auth. SCRAM is
          deferred (see plan Risk 3); prefer trust for the first green.
- [ ] 3.4 Drain to ReadyForQuery (Z): consume ParameterStatus/BackendKeyData.
          Teaching: why a client must loop until the server says it is ready.
- [ ] 3.5 Simple Query (Q): send SELECT 1; parse RowDescription (T), DataRow (D),
          CommandComplete (C), ReadyForQuery (Z). Teaching: text-format columns.
- [ ] 3.6 Row model + typed accessors (row_int/row_str parse the text column).
- [ ] 3.7 Extended query (parameterized): Parse/Bind/Describe/Execute/Sync. This is
          the scope bar. Teaching: why parameterized queries exist (injection,
          plan caching) and the extended-protocol message dance.
- [ ] 3.8 Wrap INSERT ... RETURNING, UPDATE, DELETE, SELECT for the app CRUD.
Gate: connect + SELECT 1 prints 1; a parameterized SELECT returns typed rows;
CRUD statements run against the tasks table. Every message type documented.

## Task 4 - S4: lib/std/net/http.bv (HTTP/1.1 server side)

Learning goal: HTTP is just text over TCP. Request line, headers, blank line, body.

- [ ] 4.1 Read a full request: lines until a blank line, then Content-Length bytes.
          Teaching: CRLF framing, why you must not over-read into the next request.
- [ ] 4.2 Parse request line (method, path) and headers into a small map.
- [ ] 4.3 write_response(status, content_type, body) + json_response + not_found.
- [ ] 4.4 CORS header so the browser bundle can call the API.
Gate: a real browser GET is parsed and a JSON 200 is returned (prove with the
frontend or a manual browser hit).

## Task 5 - S5: extend lib/std/web/fetch.bv (frontend HTTP client)

Learning goal: how .rbv reaches the host (frgn ... from glue/web/web.js) and how
the browser fetch maps to our stdlib wrappers.

- [ ] 5.1 Add fetch_method(url, method, body) to glue/web/web.js.
- [ ] 5.2 Add http_get/http_post/http_put/http_delete wrappers in web/fetch.bv.
- [ ] 5.3 Parse responses with json.bv on the frontend side.
Gate: an .rbv page POSTs JSON to the backend and renders the JSON reply.

## Task 6 - S6 + app: wire the three tiers together

Learning goal: see the whole data path and where each layer sits.

- [ ] 6.1 Backend app/backend/server.bv: route GET/POST/PUT/DELETE /api/tasks to
          pg.bv CRUD; serve the frontend bundle on GET /.
- [ ] 6.2 Frontend app/frontend/app.rbv: list + add + toggle + delete via fetch.
- [ ] 6.3 docs/architecture/net-stack.md: document the layer contracts + syscall
          ABI table (the permanent reference).
- [ ] 6.4 End-to-end demo: add a task in the browser, confirm it persists in PG
          and survives a backend restart.
Gate: the four CRUD operations round-trip browser -> backend -> Postgres -> back.

## Commands (pin exact invocations here as Task 0 discovers them)

Verified 2026-10-09 (Task 0). All run from a WSL shell. Sources live on the
Windows tree (/mnt/c/...); the build cache + binary live on native Linux fs via
CARGO_TARGET_DIR (see WORKFLOW.md Build and test strategy).

- brievc binary (the one carrying our fix):  /mnt/c/Users/wotto/code/briev-lang/target/release/brievc
- repo root (sources):  /mnt/c/Users/wotto/code/briev-lang

- version:
    /mnt/c/Users/wotto/code/briev-lang/target/release/brievc --version          # -> brievc 0.1.0

- check (typecheck only, fast inner loop):
    /mnt/c/Users/wotto/code/briev-lang/target/release/brievc check /mnt/c/Users/wotto/code/briev-lang/<path.bv>

- build a .bv to a native binary (stdlib auto-resolves, no flag needed):
    /mnt/c/Users/wotto/code/briev-lang/target/release/brievc build /mnt/c/.../<file.bv> --out /tmp/<outdir>
    # produces /tmp/<outdir>/<stem>.ll and /tmp/<outdir>/<stem> (the binary)

- run the produced binary:
    /tmp/<outdir>/<stem>

- rebuild the COMPILER after Rust changes (cold ~15 min first time, then fast):
    cd /mnt/c/Users/wotto/code/briev-lang && source ~/.cargo/env \\
      && CARGO_TARGET_DIR=~/briev-target cargo build --release

- run the test suite:
    cd /mnt/c/Users/wotto/code/briev-lang && source ~/.cargo/env \\
      && CARGO_TARGET_DIR=~/briev-target cargo test --lib

Toolchain note: clang-17 is the default (update-alternatives); stock clang-10
cannot parse the opaque-pointer IR the backend emits.


## Progress log (append newest at the bottom; never rewrite history)

- 2026-10-09: Branch feat/fullstack-webapp-demo created. Design + stdlib plan +
  WORKFLOW + this tasks file written. No code yet. Next: Task 0.1.
- 2026-10-09 (Task 0): brievc 0.1.0 runs. Frontend compiles Windows-side sources
  from /mnt/c with NO extra flags - default stdlib resolution works (resource root
  = the WSL clone lib/ + config/). BLOCKER found + diagnosed: Briev emits opaque-
  pointer LLVM IR (ptr type, LLVM 15+); Ubuntu 20.04 stock clang is 10, which
  cannot parse ptr -> clang error expected type. NOT a compiler bug. Installed
  clang-17 via apt.llvm.org. Briev hardcodes Command::new(clang) in src/compile.rs
  (no config/env knob) and links freestanding: -nostdlib -no-pie -ffreestanding
  (Briev .bv native programs define their own _start and use raw SysCall# for
  all I/O - no libc). Fix: point PATH clang at clang-17 via update-alternatives.
  Next: re-run brievc build hello-world, expect a working binary.
- 2026-10-09 (Task 0 COMPLETE): all four sub-steps ticked. The compile loop is
  proven end to end: edit on /mnt/c, build with /mnt/c/Users/wotto/code/briev-lang/target/release/brievc,
  stdlib auto-resolves (no --stdlib-path), binary runs. Commands pinned above.
  En route we found+fixed a compiler bug (undeclared llvm.memcpy; see BUGS.md,
  branch fix/llvm-memcpy-intrinsic-declaration, merged into this feature branch).
  Next: Task 1.1 - read bits.bv to see what Int shift/and/or ops exist for the
  byte buffer.
- 2026-10-09 (Task 1.1 DONE): bits.bv shows the bitwise ops we need are core
  infix Int operators, NOT stdlib functions: << >> & | ^ ~ are used directly in
  defn bodies (set_bit = x | (1 << i), etc). So NO prerequisite to add - bytes.bv
  can do (v >> 8) & 255 and (hi << 8) | lo at the language level. Note: >> on Int
  is a signed 64-bit shift; our protocol values are non-negative by construction.
- 2026-10-09 (Task 1.2 DONE): lib/std/net/bytes.bv created with obj ByteBuf
  {ptr;len;cap} + buf_new + buf_free. brievc check = OK. LEARNED: obj fields are
  SEMICOLON-separated, not comma (comma = parse error expected identifier). The
  plan docs comma notation was informal. Also corrected: the working brievc is at
  <repo>/target/release/brievc (built 17:59, carries the fix); the CARGO_TARGET_DIR
  redirect did not take, so ~/briev-target is empty - Commands section updated.
- 2026-10-09 (Task 1.3 DONE): put_u8 + get_u8 in bytes.bv, brievc check OK.
  put_u8(b,v)->ByteBuf: Store#(b.ptr+b.len, v, 1) then returns a NEW ByteBuf with
  len+1 (pure defn; heap mutated by Store#, record returned fresh). Precondition
  requires room (b.len < b.cap) - growth deferred to 1.6. get_u8(b,off)->Int:
  Load#(b.ptr+off, 1), precondition off < b.len (only read whats written).
  LEARNED: the proof engine proves a 1-byte Load# result is in 0..255 (accepted
  [term >= 0 && term <= 255] with no manual mask), and proved put_u8 len/cap
  postconditions. Store#(addr,val,width) / Load#(addr,width) are the byte prims.
- 2026-10-09 (Task 1.4 DONE): put_u16_be/get_u16_be + put_u32_be/get_u32_be in
  bytes.bv, all brievc check OK. Big-endian (network byte order): writers extract
  bytes most-significant-first via (val >> k) & 255 and CHAIN put_u8 (reusing its
  room contract); readers recombine get_u8 results via (hi << k) | lo. PROOF WINS:
  (1) put_u8 postconditions compose into the next calls room precondition;
  (2) engine accepts shift+mask as 0..255; (3) engine PROVES (hi<<8)|lo <= 65535
  and the 4-byte combine <= 4294967295 from per-byte <= 255. Real SMT bit reasoning.
- 2026-10-12 (ran a mini 1.7 round-trip test, integer ops): BUILT + RAN a program
  that put_u16_be(0x1234) then read it back. Output 4660 / 18 / 52 = round-trip
  value correct AND raw byte0=0x12 before byte1=0x34, proving REAL big-endian (not
  just put/get symmetry). Malloc#/Store#/Load# round-trip real heap bytes; the
  shift/mask bit math is correct at runtime. FINDING + FIX: Alloc# is NOT in the
  LLVM backends supported-intrinsic set (src/backend/llvm/normalizer.rs; only
  Malloc#/Free# via STANDARD_OPS). Alloc# worked in node_bridge.bv because that
  compiles via the GLUE host path. Changed bytes.bv buf_new to use Malloc#. The
  net-stack plan doc should say Malloc# not Alloc# (follow-up).
- 2026-10-12 (Task 1.5 DONE): put_bytes + put_cstr in bytes.bv, check OK AND
  RUNTIME-verified. put_bytes uses Copy#(dest,src,count) (bulk memcpy). put_cstr
  writes a String as NUL-terminated bytes (Postgres string framing). Test: put_cstr
  of "Hi" gave bytes 72(H) 105(i) 0(NUL) and len 3 - correct. LEARNED: a Briev
  String is [8-byte len][bytes][NUL]; byte count = text .^Length; the bytes start
  at ((text as Data) as Int) + 8 (skip the 8-byte header) - the +8 was confirmed
  only by RUNNING, check could not verify the layout. Copy# lowers to llvm.memcpy
  (relies on our bug fix).
- 2026-10-15 (traits VERIFIED, resuming D): static trait-constrained generics
  landed upstream (merged to main, PR #15; on this branch via the main merge).
  Rebuilt brievc to ~/briev-target/debug/brievc (CARGO_TARGET_DIR per WORKFLOW).
  Probe P3 (bump_twice<T: Counter>) now typechecks OK AND runs: prints 10
  (0+5+5). Previously returned Int instead of T. The byte-sink trait (design D)
  is unblocked. NOTE: test with ~/briev-target/debug/brievc, NOT the stale
  target/release/brievc (Oct 9).
- 2026-10-15 (HANDOVER - two sessions queued): resuming design D (one ByteSink
  trait, fixed + growing buffers sharing derived writers) hit a REAL codegen bug:
  a monomorphized trait DEFAULT method is emitted state-taking and its stateless
  caller passes an undefined %state. Isolated it precisely (defaults-only;
  required methods fine). Wrote handover docs so two FRESH sessions can proceed:
    1. .kiro/specs/fullstack-webapp/HANDOVER-fix-trait-default-state.md
       - FIX the codegen bug (emit_toplevel.rs ~3447 unwrap_or(true)). Own branch
         fix/trait-default-needs-state from main. BUGS.md entry OPEN 2026-10-15.
    2. .kiro/specs/fullstack-webapp/DESIGN-D-sinks.md
       - CONTINUE the feature after the fix lands. Branch feat/fullstack-webapp-demo.
  Prereq gate for session 2: probe_sink_generic.bv must build+run and print 2.
  Binary: ~/briev-target/debug/brievc (NOT target/release, which is stale Oct 9).
- 2026-10-15 (Design D, prereq gate GREEN): merged the trait-default fix to main
  (fast-forward to origin/main 46cb385c; PR #17 fix 3f08c05d landed in
  src/analysis/export_abi.rs - needs_state is DERIVED for monomorphized trait
  defaults, not defaulted true) and merged main into feat/fullstack-webapp-demo
  (merge b9f8d4de). Rebuilt ~/briev-target/debug/brievc. Gate probe_sink_generic.bv
  builds + runs + prints 2 - the monomorphized trait default is now stateless and
  its caller passes no %state. Design D is unblocked.
- 2026-10-15 (Design D, D1+D2 DONE - one coherent edit): refactored
  lib/std/net/bytes.bv to one ByteSink trait (SPEC 8.6). REQUIRED methods (on
  ByteBuf as members): put_u8 (room precond len < cap), put_bytes (room precond
  len + count <= cap). DEFAULT methods (written ONCE in the trait, over the
  required ops): put_u16_be, put_u32_be, put_cstr. Zero duplication - the derived
  writers exist in exactly one place now. DECISION (with human): did D1 and D2 as
  a SINGLE edit (Option A) rather than the staged split, because splitting would
  have left a one-commit state where a free-standing defn calls an obj member by
  bare name (an unproven path) OR required a temporary duplicate put_u8 (a
  workaround) - both rejected for production stdlib. Verified by RUNNING the two
  existing scratch tests unchanged: bytes_roundtrip.bv -> 4660/18/52 (big-endian
  u16 through the put_u16_be default), cstr_test.bv -> 72/105/0/3 (put_cstr default
  over put_bytes+put_u8 required). LEARNED (useful for the net stack): a trait
  DEFAULT method resolves at a PLAIN (non-generic, unqualified) call site on a
  concrete type - put_u16_be(buf, ...) on a ByteBuf reaches the default and its
  put_u8 calls dispatch to ByteBuf's member. No generic/qualified call needed, so
  existing callers did not change a line. Contracts preserved: put_cstr no longer
  carries an explicit room precondition (correct - a default stays pure over the
  required primitives; the room obligation is enforced transitively by put_bytes
  and put_u8). Next: D3 - add GrowBuf (growing implementer, realloc on overflow).
- 2026-10-15 (Design D, liveness bug found + fixed, D3 CONFIRMED): building D3's
  GrowBuf surfaced a REAL compiler bug (NOT feature logic): defn-liveness indexed
  obj member bodies by BARE name with first/last-wins, so two objs with a
  same-named member (ByteBuf.put_u8 declared before GrowBuf.put_u8) collided -
  only one body survived the reachability walk. Rooting GrowBuf's put_u8 walked
  ByteBuf's helper-free body, missed the call edge into free-standing grow_to_fit,
  judged it dead -> the IR-scan net panicked 'unreached defn [grow_to_fit]'.
  Isolated with a controlled A/B (single member -> 7; add same-named member -> 
  panic). FIX on fix/liveness-member-name-collision (from main): a collision-safe
  member_bodies multimap keeps EVERY same-named member body+contract and the
  worklist walks them all when the name goes live. +2 regression tests, cargo
  test --lib green, pushed to fork, PR write-up in PR-liveness-member-collision.md.
  Awaiting merge to main. WORKING BRANCH feat/d-sinks-integration (feat branch +
  fix merged) lets us keep building D; the clean feat/fullstack-webapp-demo will
  pick the fix up via main later (final feature history carries no direct fix
  copy). With the fix in, growbuf_test.bv builds + RUNS: start cap 2, put 10/20/
  30/40/50 (forces reallocs 2->4->8), read all five back = 10/20/30/40/50, len 5.
  Proves the realloc+Copy#+Free# preserves data across ptr moves and the SAME
  put_u8 call site works as ptr changes underneath. D3 done. Next: D4 - one
  generic writer over BOTH ByteBuf and GrowBuf (the payoff).
- 2026-10-15 (Design D, SECOND compiler bug found + fixed, D4 CONFIRMED): D4
  (one generic writer over BOTH sinks) surfaced ANOTHER real compiler bug: a
  trait default/generic monomorphized onto a type with STATEFUL members was
  emitted stateless, so write_tagged$GrowBuf/put_cstr$GrowBuf called the
  genuinely-stateful grow_to_fit(ptr %state, ...) with an undefined %state.
  Type-dependent: put_cstr$ByteBuf is genuinely stateless (Store#/Copy#), but
  put_cstr$GrowBuf is stateful (Malloc# via grow_to_fit). ROOT CAUSE (export_abi.rs
  + emit_expr.rs): (1) the needs-state fixpoint never indexed obj members, so a
  default's bare call to a required method saw an unknown external (stateless) and
  the member->member->Malloc# path was invisible; (2) the monomorphization site
  copied the single type-agnostic base verdict, unable to differ per concrete Self.
  FIX on fix/needs-state-type-dependent-members (from main): index obj/impl members
  under type-qualified keys (ByteBuf::put_bytes vs GrowBuf::put_bytes = distinct
  nodes); derive type_stateful_members from the same fixpoint; at the specialization
  site OR 'any concrete binding has a stateful member' into the mono verdict. +2
  regression tests, cargo test --lib green, pushed to fork, PR write-up in
  PR-needs-state-type-dependent-members.md. Awaiting merge to main.
  With BOTH fixes on the working branch (feat/d-sinks-integration = feature +
  liveness fix + needs-state fix), D4 BUILDS + RUNS: write_tagged<S: ByteSink>
  writes a u16-BE tag 0x1234 then put_cstr "Hi" into a ByteBuf (cap 16) AND a
  GrowBuf (cap 2, forcing a mid-write realloc), reading back 18/52/72/105/0 from
  BOTH. The SAME generic code path serves both sinks with identical bytes - the
  payoff of design D (shared derived logic over per-type primitives), with the
  growing buffer's realloc transparent to the generic writer. D4 done. Next: D5 -
  update the net-stack plan S1 row (Alloc#->Malloc# note, bytes.bv now exposes the
  ByteSink trait), behavioral tests + a .bv example, then the branch replay so the
  clean feat/fullstack-webapp-demo carries the feature once both fixes land on main.

## Load-harness compiler PRs — 2026-11-03

Submitted clean, independent fix branches from upstream main `373e548e` to fork;
PRs target Randozart/briev-lang main. The integration branch was not submitted.

- [PR #57](https://github.com/Randozart/briev-lang/pull/57):
  `fix/discarded-enum-payloads`, `b8da475b`; body `PR-discarded-enum-payloads.md`.
- [PR #58](https://github.com/Randozart/briev-lang/pull/58):
  `fix/enum-result-capture`, `a62c5282`; body `PR-enum-result-capture.md`.
- [PR #59](https://github.com/Randozart/briev-lang/pull/59):
  `fix/collection-index-writes`, `8859ae9b`; body `PR-collection-index-writes.md`.

No merge-order dependency among these three. Preserve all BUGS entries on append
conflicts. PR body documents remain untracked and locally Git-excluded. Each
published body was read back and matched against its local document.

Clean-branch library suites: 3,440 / 3,440 / 3,445 passed respectively. Native
regressions, full seven-case IR determinism and Clang 17 recommender checks pass.
Two dataset-dependent matrix rows skip explicitly because u.data is absent.
Only the long conformance sweep is left to upstream CI, per user instruction.
Praetor adds no diagnostic categories. Collection carve-out preserves upstream
browser commit boundaries and uses the current centralized enum query.

Stdlib/harness features and general collector ownership leaks remain outside
these compiler PRs. Interpreter indexed-write parity remains open.

## PR #59 conformance follow-up — 2026-11-04

`fix/collection-index-writes` now points to `58cdbe21`. The five upstream
failures reproduce on `8859ae9b` and pass on the updated compiler. Full local
`cargo test --lib` passed all 3,450 tests, including conformance, with zero
filtered out. The independent Windows CRLF data-line issue and the exact
committed fixture used for local verification are documented in the PR body.
