# Full-stack web app: Briev net stack + stdlib build-out (2026-10-09)

**Status:** ACTIVE - planning. Branch: feat/fullstack-webapp-demo.
**Companion app spec:** .kiro/specs/fullstack-webapp/design.md (the demo app that
drives this work; the app is a vehicle, the stdlib/compiler work below is the goal).

## Purpose

Build a full-stack web application entirely in Briev - frontend (.rbv), backend
(.bv native server), and a real database connection (PostgreSQL over its wire
protocol) - with NO other languages (no Python, no Node, no C library for the DB).
The app is small on purpose; the point is to grow the standard library and surface
compiler bugs. Every capability the app needs that the stdlib lacks becomes a
tracked stdlib deliverable here.

## Ground truth (verified against the tree at 475bb749)

- SysCall# is REAL and sufficient: lib/std/syscall.bv wraps SysCall#(nr,a1..a6)
  (observable:true) as syscall1..syscall6 with [nr>0][nr<512] contracts.
  examples/glue-host/node_bridge.bv already does file I/O with literal syscall
  numbers (open=2, read=0, write=1, close=3, lseek=8) plus Alloc#/Load#/Store#.
  Sockets are reachable the same way (socket=41, connect=42, bind=49, listen=50,
  accept=43, sendto=44/write=1, recvfrom=45/read=0, setsockopt=54).
- os/net.bv and os/fs.bv are EMPTY STUBS: both contain only repeated SYS_WRITE/
  SYS_READ const lines, no functions. (BUG to log - see Risks.)
- Frontend surface is real: lib/std/web/{dom,router,fetch,console}.bv, b-trigger/
  b-when/b-window directives, frgn ... from glue/web/web.js. fetch(url)->String
  exists; we extend it for methods/headers/body.
- Real stdlib we build on: string, string_builder, json, collections, hashmap,
  iterator, encoding, time, result, option.

## Architecture: five layers, bottom-up

Each layer is a stdlib module (or a documented extension of one). Every new module
ships with contracts, behavioral tests, and a short architecture note, per AGENTS.md.

```
L5  app       .kiro demo app: .rbv frontend  +  .bv backend
L4  http      lib/std/net/http.bv    HTTP/1.1 request parse + response build
L3  pg        lib/std/db/pg.bv       PostgreSQL v3 wire client
L2  socket    lib/std/net/socket.bv  TCP sockets over SysCall#
L1  bytes     lib/std/net/bytes.bv   byte buffer: read/write ints, slices
L0  syscall   lib/std/syscall.bv     EXISTS (SysCall# wrappers)
```

### L1 - bytes (lib/std/net/bytes.bv) NEW

Raw byte buffers backed by Malloc#/Load#/Store#/Copy#. The wire protocols need
precise byte-level framing that String concat cannot express.

CORRECTION (2026-10-12): Alloc# is NOT in the LLVM backend's supported-intrinsic
set — bytes.bv uses Malloc#/Free# (Alloc# worked only on the GLUE host path).

DESIGN D (2026-10-15): the derived network-byte-order writers are shared across
two buffer flavors via ONE trait (SPEC §8.6), not duplicated:

- trait ByteSink
  - REQUIRED (each buffer provides, with its own contract):
    put_u8(sink, v) ; put_bytes(sink, src_addr, n)
  - DEFAULT (written once in the trait, over the required primitives):
    put_u16_be(sink, v) ; put_u32_be(sink, v) ; put_cstr(sink, s: String)
- obj ByteBuf { ptr, len, cap } — FIXED: put_u8 keeps a `len < cap` room
  precondition; ptr is stable (never moves). buf_new(cap) / buf_free(b).
  Readers: get_u8 / get_u16_be / get_u32_be.
- obj GrowBuf { ptr, len, cap } — GROWING: put_u8/put_bytes have NO room
  precondition; on overflow grow_to_fit reallocates (Malloc# double-or-enough,
  Copy#, Free#, new ptr). grow_new(cap) / grow_free(b) / grow_get_u8.

Conformance is structural: an obj providing the required methods (with refining
contracts) satisfies the trait — no impl block. A function generic over
`<S: ByteSink>` serves both buffers with one implementation (see
examples/net-bytes-sink.bv).

WATCH-FOR: a growing put MOVES ptr. Length-prefix backpatching (Postgres, Task 3)
must use the FIXED ByteBuf or store OFFSETS, never cached interior addresses.

Contracts: offsets in [0,len); big-endian is explicit (Postgres and HTTP chunk
sizes are network byte order).

Compiler surface exercised: Malloc#/Load#/Store#/Copy# with computed offsets,
Int<->byte masking (bits.bv shifts/and at the language level), obj with mutable
Int fields, pointer-as-Int, SPEC §8.6 trait defaults + structural conformance
monomorphized onto two concrete types. (En route this exercised — and fixed —
three compiler bugs: trait-default %state, defn-liveness member-name collision,
and type-dependent needs_state for monomorphized members; see BUGS.md.)

### L2 - socket (lib/std/net/socket.bv) NEW

TCP client + server sockets via raw syscalls (Linux x86_64 numbers; documented as
literals because SysCall# resolves literals/abstract op names, NOT named consts).

- tcp_connect(host_ip: String, port: Int) -> Int   (returns fd, or <0 on error)
    socket(AF_INET=2, SOCK_STREAM=1, 0) then connect() with a packed sockaddr_in
- tcp_listen(port: Int, backlog: Int) -> Int   (socket+bind+listen, returns fd)
- tcp_accept(listen_fd: Int) -> Int   (returns client fd)
- sock_send(fd, ptr, n) ; sock_recv(fd, ptr, n) ; sock_close(fd)

sockaddr_in is a 16-byte struct built in an Alloc# block: family(u16 LE)=2,
port(u16 BE), addr(u32 BE), 8 zero bytes. IPv4 dotted-quad parse lives here.

Scope cut: no DNS, no IPv6, no TLS. Postgres and the browser talk to 127.0.0.1.
Blocking sockets only; the server handles one connection at a time in v1.

### L3 - pg: PostgreSQL v3 wire client (lib/std/db/pg.bv) NEW - headline deliverable

Pure-Briev client speaking the PostgreSQL frontend/backend protocol v3.0 over a
tcp socket. No libpq. Scope bar (agreed): connect, parameterized query, read typed
rows. Transactions and full type decoding are stretch.

Messages implemented (minimum viable client):

- Startup: StartupMessage(user, database). Handle AuthenticationOk; support
  cleartext + MD5 auth (encoding.bv has hex). SCRAM is the modern default - see
  Risks; may need a scram helper or a trust/md5 pg_hba for the demo.
- Simple query: Query -> RowDescription, DataRow*, CommandComplete, ReadyForQuery.
- Extended query (parameterized, the scope bar): Parse/Bind/Describe/Execute/Sync
  -> ParseComplete, BindComplete, RowDescription, DataRow*, ReadyForQuery. Params
  sent as text format; results read as text (format code 0) in v1.
- Terminate on close.

Row model: obj Row { cols: [String] } with typed accessors row_int(r,i) /
row_str(r,i) that parse the text column. obj PgConn { fd, ... }.

Compiler surface exercised: the hardest test - stateful binary protocol framing,
message-type dispatch (match on a byte), length-prefixed reads, loops over a
variable row count. This is where we expect to find the most bugs.

### L4 - http (lib/std/net/http.bv) NEW

Minimal HTTP/1.1 over a tcp socket. Server-side for the backend.

- parse_request(fd) -> Request { method, path, headers, body }  (read to blank
  line, then Content-Length bytes). Reuses encoding.bv/string.bv.
- write_response(fd, status, content_type, body).
- Helpers: json_response(fd, status, body), not_found(fd). Routing is the app.

Scope cut: one request per connection, no keep-alive, Content-Length only.

### L5 frontend - extend web/fetch.bv

Current fetch(url)->String is GET-only. Extend the glue + stdlib so the frontend
can POST/PUT/DELETE JSON:

- frgn fetch_method(url, method, body) -> String  (glue/web/web.js addition)
- http_get/http_post/http_put/http_delete wrappers in web/fetch.bv
- The .rbv app renders the task list from JSON (json.bv parse) and calls these on
  b-trigger:click.

NOTE: the browser cannot open a raw TCP socket, so the frontend talks HTTP to the
.bv backend; only the BACKEND speaks the Postgres wire protocol. This is the
correct and only architecture.

## Deliverables ledger (track here)

| ID | Module | New/Extend | Scope-bar gate |
|----|--------|-----------|----------------|
| S1 | lib/std/net/bytes.bv  | NEW ✓ DONE 2026-10-15 | ByteSink trait: ByteBuf (fixed) + GrowBuf (growing) share derived BE writers as defaults; round-trip u8/u16/u32/cstr on both; generic `<S: ByteSink>` serves both. Gate: tests/tier1/byte_sink_trait_smoke.bv (golden "18527210501852721050" in daily_use_smoke.rs) + examples/net-bytes-sink.bv |
| S2 | lib/std/net/socket.bv | NEW ✓ DONE 2026-10-16 | TCP client + server over raw syscalls: sock_tcp/connect/send/recv (partial-transfer loops, MSG_NOSIGNAL), sock_bind_listen/accept, set_nonblocking + SO_REUSEADDR; 16-byte sockaddr_in built from the L1 ByteSink writers via dot chaining; -errno via obj Socket. Gate: tests/tier1/socket_loopback_smoke.bv loopback round-trip (golden in daily_use_smoke.rs), brievc check clean. Two compiler bugs found+fixed (BUGS.md 2026-10-16): dot-dispatch explicit-receiver args; -> Void defn called as a statement. |
| S3 | lib/std/db/pg.bv      | NEW    | connect + SELECT + parameterized query, typed rows |
| S4 | lib/std/net/http.bv   | NEW    | parse a real browser GET, write a JSON 200 |
| S5 | lib/std/web/fetch.bv  | EXTEND | POST/PUT/DELETE JSON from .rbv to backend |
| S6 | docs/architecture/net-stack.md | NEW | document layer contracts + syscall ABI |

Each S-item: contracts + behavioral tests (cargo test --lib and/or a .bv gate) +
brievc check green + Praetor no-new-diagnostics on changed dirs + BUGS.md entries
for anything found. New .bv stdlib files must pass the conformance sweep.

## Risks and open questions (the interesting part)

1. os/net.bv + os/fs.bv are corrupted stubs (repeated SYS_WRITE consts). Likely a
   generator bug or bad merge. ACTION: log in BUGS.md; build the real modules under
   lib/std/net/ rather than editing the stubs.
2. SysCall# literal-vs-const resolution: node_bridge.bv warns a named const
   (SYS_OPEN) is NOT resolved and silently falls to 0. We MUST use literal numbers.
   A sharp edge worth a compiler diagnostic.
3. Postgres auth: modern PG defaults to SCRAM-SHA-256 (HMAC/SHA-256 + base64 +
   nonce). Mitigation for the demo: configure PG with trust or md5 auth. SCRAM is a
   stretch stdlib item (lib/std/crypto/). Log the gap.
4. Byte-accurate Int<->bytes needs bits.bv shifts/masks on Int. Verify bits.bv has
   shl/shr/and/or on Int; if not, that is a prerequisite stdlib addition.
5. Socket reads return partial data; readers loop until expected length. A txn with
   [got<need][got==need] is the natural shape.
6. Does the LLVM backend allow a long-running accept-loop program (no fold to dead
   code)? The server never halts; observability comes from send() FFI. Confirm the
   optimizer does not elide the loop (observability-as-liveness, AGENTS.md).
7. String is UTF-8/Char-based; raw bytes live in ByteBuf, never String. Keep the
   byte boundary strict: String only at the text edges.

## Suggested sequencing

1. S1 bytes (+ any bits.bv prereqs) - pure, unit-testable, no network.
2. S2 socket - prove tcp_connect against the local PG port accepting a connection.
3. S3 pg - connect + SELECT 1 first, then RowDescription/DataRow, then parameterized.
4. S4 http + S5 fetch - backend serves the app; frontend calls it.
5. S6 docs + wire the .kiro demo app end to end.

## Bug / finding log (append as we go)

- 2026-10-09: os/net.bv and os/fs.bv are empty stubs (repeated consts). Pending
  BUGS.md entry.

(Compiler bugs found during implementation get a BUGS.md entry AND a line here with
the date, the .bv snippet that triggered it, and the workaround.)

### 2026-10-21 — relative code-import path bug (verification pending)

Task 10.1 gate fails before typechecking: `../examples/recommender/udata.bv`
becomes `///examples/recommender/udata.bv`. Minimal trigger is the first import
in `scratch/udata_gate.bv`. The code resolver expands namespace dots inside
filesystem-relative paths. Fix authored on `fix/relative-import-paths` with
regression coverage; no application workaround. Human verification pending.

### 2026-10-21 — relative import fix verified

`fix/relative-import-paths`: preserve filesystem-relative path spelling via
code_module_path; bare dotted module names retain their namespace expansion.
Human reports post-refactor cargo check, cargo test --lib, and cargo build green;
the native parser gate previously passed all six checks. Controlled Praetor
before/after diagnostics match. Compiler PR is prepared before feature work resumes.

### 2026-10-21 — schema gate exposes pointer-valued collection store (OPEN)

Native schema-gate build fails inside pg_decode_fields before any DB connection:
a singleton List<String> stores its ptr-valued element as i64 without conversion.
Generated IR proves the type mismatch for both literal and decoded text.
Controlled Int/String singleton probes authored, human verification pending.
No pg.bv workaround. See the pointer-valued-collection-store investigation plan.


### 2026-10-21 — generic literal argument type loss isolated

Int list concatenation succeeds; String list concatenation reproduces the
schema-gate ptr/i64 failure without net/db imports. The compiler constructs
inline generic-call arguments using unspecialized List<T>. Frontend fix authored
on fix/generic-call-literal-types, preserving the inferred collection type in a
typed value block. Generic-call and operator-call paths share the helper.
Unit/native verification pending human execution; application code unchanged.

### 2026-10-21 — generic literal fix regression corrected, retest pending

Full-suite output exposed empty tuple accumulators losing their declared return
context during elaboration. Initialize current_output_type for defns and txns
as ordinary typechecking already does. Dedicated accumulator regression added;
no tests disabled or stdlib workarounds. Human filtered/full-suite reruns pending.

### 2026-10-21 — generic literal argument fix verified

Human reports full suite green after declared-return context correction. Native
String concat gate: four true checks; Int control: two true checks. Reduced
original failure is resolved without stdlib changes. Praetor has no increased
metrics or added diagnostics. Commit/PR approval pending; full schema gate will
be rerun on the integration branch after the separate compiler PR handoff.

### 2026-10-21 — terminating match arm suppresses value merge (OPEN)

After loading 100,000 baseline ratings, engine-adapter verification exposed a
compiler defect independent of Result/app code: a match with one trap arm loses
the continuing arm's result phi. Minimal value/value control compiles, value/trap
fails LLVM. Fix/tests authored on fix/match-terminating-arm-values; human cargo
verification pending. Feature work is preserved in the documented scratch patch.

Verification: four focused regressions and native value/trap gates pass; cargo
build passes. Full suite: 3157 passed, 38 known failure names, none added.

## PostgreSQL receive buffer metadata (FIXED 2026-10-21)

pg_read_msg filled memory without publishing ByteBuf.len, so bounded error-field
scans returned empty SQLSTATE/message. buf_received now publishes initialized
header/body prefixes without copying or creating a second allocation owner.
Standalone tests/fixtures/stdlib/pg_receive_gate.bv passes prefix invariants and
live 22012/division by zero preservation through rollback and connection reuse.
Integration build passes; library suite: 3164 passed, 38 known failures, none new.
Praetor directory checks pass. No compiler source changes or performance claim.
Branch fix/pg-receive-length targets feat/net-db-postgres, absent from main.

## Result wrong-side unwrap fabricated payloads (FIXED 2026-10-21)

unwrap and unwrap_err fabricated cast fallback values instead of their documented
trap. Wrong sides now trap; actual payloads are preserved. Standalone regression
tests/fixtures/stdlib/result_object_gate.bv passes both object payloads and both
wrong-side SIGILL paths on integration. Depends on compiler fix 23cbbdac; this
stdlib branch carries no compiler changes. Integration build passes; library
suite: 3164 passed, 38 baseline failures, no added failure names. Praetor passes.

Task 10 complete (2026-10-21): native parser/bootstrap/population/upsert gates
pass, including batch rollback and concurrent startup. Integration suite: 3164
passed, 38 known failures, none added. Stdlib fixes have separate PR branches
fix/pg-receive-length and fix/result-wrong-side-unwrap; task-10 commit excludes
those edits. See docs/plans/2026-10-21-recommender-bootstrap.md for evidence.

Task 11 native account service (2026-10-21): atomic parameterized registration,
FNV demo storage, explicit random-token sessions and token-authenticated state
pass their native gates (144 credential and 120 isolation cases). The human
confirmed recommendation composition belongs to task 12, using this same owner.
No compiler/stdlib fix needed; docs/plans/2026-10-21-recommender-accounts.md records
the increments and tests. Full library suite is running; commit approval pending.

Task 11 final gates (2026-10-21): native corpus and fresh-connection login/state
persistence pass. Full library suite: 3164 passed, 38 baseline failures with
exactly the same names as task 10. Praetor passes; no compiler/stdlib changes.

Task 12 (2026-10-21): implemented native poll HTTP routing, token-owned live
channels, buffered partial writes, active-account predictions and consistent
periodic/explicit snapshot refresh. Native gates exposed and fixed collection
rebinding (compiler) and JSON consume-or-error progress/framing (stdlib); see
BUGS.md and docs/plans/2026-10-21-recommender-server.md. Compiler fix is prepared
on its own main-based branch. Interpreter changes are excluded by explicit user
instruction. Final native/property/library verification is recorded in the task
plan; no throughput/latency claim is made before task 16.

I09 view compiler UTF-8 cursor (2026-10-23): generated recommender HTML exposed
a view compiler cursor bug. Copying a multibyte scalar advanced the byte offset
by one, corrupting later injected directive tags. `ViewCompiler::inject_ids_inner`
now advances by `char::len_utf8()`, with a regression that puts accented, CJK
and punctuation text before directives. The human runs Cargo tests/rebuild per
WORKFLOW.md; the existing WSL `brievc` binary predates this Rust edit. I09 keeps
static template punctuation ASCII until the rebuilt compiler verifies Unicode
output.

## 2026-11-01 compiler bug log: nested object enum image

Recommender SavedRating(RatingSaved) exposes an inline enum image smaller than
the resolved object payload. Minimal repro and fix status: BUGS.md entry dated
2026-11-01; execution record docs/plans/2026-11-01-recommender-compiler-closure.md.
No stdlib/app workaround; planner must consume resolved object byte sizes.

### 2026-11-01 callable transaction entry allocation

The recommender selection loop exposes a module-level alloca emitted by the
callable transaction prologue. Minimal repro: scratch/callable_txn_local_slot.rbv.
Move the prologue into entry, before parameter bindings; no stdlib workaround.

### 2026-11-01 enum field context

OwnedOperationJob inside an object inherited the enclosing Result return layout.
Field emission must scope constructors to the declared field enum; no app workaround.

### 2026-11-01 inline object projection lifetime

Worker startup exposes unwrap returning an inline object's interior pointer into
a stack enum image. Bound object values must own an image before escaping; no
application workaround. Runtime evidence and status are in the closure plan.

### 2026-11-01 nested enum object ABI

Save decoding exposes differing nested/standalone object payload capacities.
Finite object images must not change representation at the enum recursion cap.

### 2026-11-01 inline member commit boundary

Repeated selection renders came from collection At members publishing the outer
transaction on their own term. The generated-host experiment reduced 14 flushes
per click to one. Scope inline member context and retain only the outer commit;
see docs/plans/2026-11-01-recommender-selection-commit-boundary.md.

### 2026-11-03 compiler regression closure

Raw `Bits<N>` encoding lost its constructor when Data-to-String became a
representation cast. Restored a distinct graph edge, corrected concrete bit
casts from pointers and widening integers, and verified native/browser round
trips without an app workaround. The tuple test's i64-only expectation was
obsolete after upstream's target-width handle migration; both target widths
and a browser return/destructure fixture now cover the intended ABI. See
`docs/plans/2026-11-03-cast-and-tuple-regressions.md` for verification.

## 2026-11-03 — load-harness compiler fix submissions

The load work's native compiler fixes were carved from upstream main 373e548e
and submitted independently: #57 discarded enum payload allocations
(b8da475b), #58 enum result capture contract (a62c5282), and #59 indexed
collection writes/storage (8859ae9b). See the fullstack task map and untracked
root PR body documents for links, controlled A/B evidence and exact validation.
No stdlib or application workaround is included. The collection branch adapts
to upstream's centralized enum query and retains newer browser publication
rules. Native gates and clean-branch library suites pass; the long conformance
sweep is delegated to upstream CI. Broad returned-value lifetime closure and
interpreter indexed-write parity remain open rather than being claimed fixed.

## 2026-11-04 increment — nested environment expansion

The collector probe exposed an unresolved nested `get_env_int!` intercept.
The environment plugin's partial walker omitted control-flow/operand positions
and intercept arguments. Migrate it to the shared exhaustive postorder visitor;
preserve constants, receiver-first calls and unknown plugin nodes. Focused
regressions and native end-to-end verification are in progress. No harness
workaround or bounded-memory claim is introduced.

Expansion verification: 3 focused unit tests, native integration and 3,441
library tests pass; only the delegated conformance sweep is excluded. Build
passes without new warnings and quick IR determinism passes all three corpus
programs. Select the installed current SPIR-V validator and LLVM 17 tools on
PATH. No reclamation change or load-testing readiness claim follows.

## 2026-11-04 increment — collector memory closure

General frontend allocation/alias/escape facts now license hosted native call
regions. The runtime tracks actual allocator results, preserving caller images
and borrowed/static payloads, and handles explicit free/realloc and failures.
No collector-level frees or helper-name compiler exceptions were added.

All nine Valgrind cases pass with zero definite/indirect loss and memory errors.
Two 5,000-sample runs at 500 Hz stay flat after warmup: RSS 355 and 378 pages,
virtual memory 3,989,504 bytes in both. Full load functional checks pass.
Native alias/runtime and both wasm gates pass; library verification passes
3,459 tests with only the delegated source conformance sweep excluded. Compiler
build and all seven IR determinism corpus programs pass. Kani cannot start on
the executor's older glibc; the harnesses are not claimed formally verified.

The investigation also fixed runtime-reflection liveness, missing/colliding LLVM
attribute groups, tail-execution frame retention and wasm allocator/store widths.
Evidence, target limits, commands and hashes:
`docs/plans/2026-11-04-collector-reclamation-closure.md`. The application load
plan is `C:/Users/wotto/code/recommender-app/docs/plans/2026-11-03-briev-native-load-harness.md`.
Memory repair is complete in the working checkout; backend capacity and sustained
application campaigns remain unmeasured. Commit/carve-out awaits workflow approval.

## 2026-11-05 — load collector checkpoint and resource bug log

- [x] Reproducible collector checkpoint committed in recommender-app as
  `80aae72`; execution record is
  `../recommender-app/docs/plans/2026-11-05-collector-checkpoint.md`.
- Minimal resource trigger: `read_file("/proc/self/stat")` repeated, or
  `read_file("/proc/self")` returning EISDIR. Main leaked the opened descriptor.
  Proper fix: retain read_whole's result, close the descriptor, return that
  result. No harness workaround. Independent branch `6850858a`, PR #63:
  https://github.com/Randozart/briev-lang/pull/63.
- Collector prerequisites are a separate clean feature, `c403e943`, PR #64:
  https://github.com/Randozart/briev-lang/pull/64. No compiler Rust changes.
- `integration/load-collector-verified` at `68e81bf1` combines both branches
  in the load-collector-prerequisites carve-out worktree. Both branches and
  integration passed 3499 library tests; the source sweep remains CI-delegated.
- Ten Valgrind cases pass. Two 5000-row runs at 500 Hz have zero missed arrivals,
  RSS flat at 373 and 393 pages after warmup, and VM fixed at 3989504 bytes.
  These establish collector readiness, not target capacity or endurance.
- This dirty integration's Data alias cast conflicts with main's formatter
  copy-and-free assumption. Preserve the work; use the verified clean-main
  integration for this checkpoint. The unresolved tuple transport probe is next.

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
