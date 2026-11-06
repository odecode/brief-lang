# Recommender responsiveness: implementation tasks and parallel work map

Created 2026-10-22. Status: **I01 baseline and I02 contracts integrated/verified**.
The human approved the architectural direction and requested this task list to
evaluate parallel-agent execution. This document does not start agents or code
changes. All implementation tasks are initially unchecked and unassigned.

Plan of record: [recommender responsiveness](../../../docs/plans/2026-10-22-recommender-responsiveness.md).
Work branch: `recommender-proof-of-concept` (formerly
`integration/ptr-provenance`). Starting application checkpoint: `6fb27e01`.
Verify actual HEAD and working-tree state at execution time.

## Start here

Read the plan completely, plus its fresh-session reading list and WORKFLOW.md.
The plan's DRAFT header predates the human's approval; the approval is recorded
here without rewriting the historical plan. Dependencies below refine execution
order; they do not relax the plan's correctness or performance requirements.

The agent runs cargo, brievc and other necessary commands, per the human's
session override. Preserve the existing 38 accepted environment failures and
unrelated working files. Follow WORKFLOW's compiler/stdlib/application carve-out
rules. Pushes, PR creation and merges are separate from this task-list request.

Avoid running the lib and other large test suites as much as possible because they take a long time. Run them only as final validations.

Non-negotiable outcome:

- Accepted in-memory ratings independently feed prediction and persistence.
- Pending feedback paints immediately; saved confirmation follows DB commit.
- Save completion never triggers prediction or a recommendation DOM update.
- Prediction uses current in-memory profile plus an immutable shared model.
- HTTP and WebSocket submissions use one admission/idempotency service.
- Ordering, stale-result rejection, account isolation, bounded resources and
  truthful save status remain mandatory despite relaxed model freshness.
- No production server/DB logic is moved out of Briev. Browser adapters remain
  general host APIs exposed through Briev stdlib. No algorithm recognition in Rust.

## Scheduling and ownership rules

`Depends on` means every listed task must be integrated and its acceptance gates
must pass before dependent implementation starts. A branch that merely exists,
a draft API, or another agent's progress message does not satisfy a dependency.
Early read-only investigation is allowed; do not code against guessed interfaces.
Tasks described as concurrent still require disjoint file and resource ownership.

Use one coordinator/integrator and, initially, up to three implementation agents.
The coordinator owns the shared branch, dependency ledger, cross-module wiring,
specification changes and shared-runner edits. Workers own the files allocated to
their claimed task, including task-specific tests and documentation fragments.
This is a proposed arrangement, not a request to launch agents now.

For each assignment record task ID, owner, branch/worktree, base commit, writable
paths, test resources and expected handoff. Prefer separate worktrees for actual
parallel editing. Never switch a shared checkout's branch while another agent is
using it. With a shared directory, prohibit overlapping writes and serialize git
index/commit operations through the coordinator. No global staging or restoring.

Shared hot files are coordinator-only unless explicitly handed off for one task:
`server_state.bv`, `server_loop.bv`, `server_live.bv`, `server_api.bv`, `server.bv`,
`app.rbv`, `store.bv`, existing shared fixture runners, this list, BUGS.md, and
central architecture/specification documents. Module names proposed below are
boundaries to finalize in I02, not permission to duplicate existing helpers.

Task-local gates should use new narrowly named fixture modules/runners; the
coordinator wires them into shared runners at integration. Each worker supplies
architecture/bug-note text in its handoff, and the coordinator incorporates it
in the SAME logical integration commit. Preserve rationale comments.

Database tests need distinct databases or verified independent schemas; existing
runners with fixed reset schemas must never run concurrently in the same DB.
Give each lane unique ports, CACHE_PATH, artifact/output directories and worker
IPC paths. Keep benchmark measurements exclusive: no cargo builds, load tests or
other CPU/DB-heavy gates during controlled timing. Compiler builds/tests sharing
one cargo target directory are serialized; private caches are costly, not free.

## Dependency matrix

| ID | Deliverable | Depends on | Suggested owner / concurrent work |
| --- | --- | --- | --- |
| I01 | Correct baseline and stage instrumentation | None | Coordinator; read-only contract investigation may overlap |
| I02 | Versioned interfaces, state machines and file allocation | I01 | Coordinator; synchronization gate before parallel code |
| I03 | General async browser HTTP API | I02 | Browser lane; concurrent with I04/I05/I06 |
| I04 | Pure profile/admission state machine | I02 | State lane; concurrent with I03/I05/I06 |
| I05 | Bounded IPC and persistent-worker lifecycle | I02 | Worker lane; concurrent with I03/I04/I06 |
| I06 | Exact active-profile engine and scratch reuse | I02 | Engine lane; concurrent with I03/I04/I05; measurement-gated |
| I07 | Durable operation receipts and ordered persistence | I04, I05 | Persistence lane; concurrent with I08/I09 |
| I08 | Prediction pool, coalescing and model generations | I05, I06 | Prediction lane; concurrent with I07/I09 |
| I09 | Async browser migration and optimistic state | I03, I04 | Browser lane; concurrent with I07/I08 |
| I10 | Reactor admission, hydration and publication wiring | I04, I07, I08 | Coordinator; serialize edits to shared server files |
| I11 | Real browser/server protocol integration | I09, I10 | Coordinator + browser lane with explicit file handoff |
| I12 | Refresh with pending overlays and worker generations | I10 | Coordinator; may overlap I11's browser-only work |
| I13 | Reconnect, retry, epoch and shutdown integration | I11, I12 | Coordinator; serialize overlapping state edits |
| I14 | Native failure/concurrency verification | I13 | Verification lane; concurrent with I15 on isolated resources |
| I15 | Browser responsiveness and recovery verification | I13 | Browser verification lane; concurrent with I14 |
| I16 | Controlled before/after performance acceptance | I14, I15 | Exclusive measurement window; no competing jobs |
| I17 | Final regression gates, docs and reviewable handoff | I16 | Coordinator; completion gate |

All dependencies are AND dependencies. The table is the source of truth for
readiness; every detailed task below uses the same prerequisite set.

With three worker slots, an example schedule is:

1. Coordinator completes I01 and I02.
2. Run I03, I04 and I05 in parallel; run I06 as a slot becomes free. I06's
   measurement window pauses competing heavy work even though code is independent.
3. After prerequisites land, run I07, I08 and I09 in parallel.
4. Integrate I10; I11 browser integration and I12 refresh can overlap only with
   explicit file ownership. I13 is the next shared-state synchronization gate.
5. Run I14 and I15 independently, reserve an exclusive I16 window, finish I17.

This permits useful parallel work without pretending all server/UI wiring is
independent. Worker infrastructure and immutable interface contracts are the
main enabling tasks; shared reactor integration is deliberately serialized.

## Tasks

### I01 — Establish a trustworthy baseline

- [x] Claim coordinator ownership and capture branch/commit, dirty files, service
  processes, compiler binary and accepted library-test failure names.
- [x] Create a dated execution/results record and an isolated measurement setup.
  Use the existing benchmark harness; record ALL runtime benchmark results after
  a clean release build, including existing failures. Historical numbers are context.
- [x] Add correlation and monotonic stage instrumentation through the CURRENT
  click/save/GET/push/render path without changing application behavior.
- [x] Establish browser pending-feedback and fresh-recommendation paint timings,
  DB query/protocol time, calculation stages, preflight and queueing costs.
  Measure eligible accounts, not only zero-rating cold-start responses.
- [x] Gate: reproducible baseline artifacts identify commit/config/geometry,
  actual served binaries, stage costs and correctness checks. No performance
  implementation starts until the baseline is complete.

### I02 — Freeze integration contracts and allocate files

- [x] Specify Briev types/functions and wire schemas for operation ID, server
  epoch, account revision, model generation, accepted/saved/failure/result events.
  Define JSON compatibility and errors, HTTP fallback/reconciliation endpoints,
  and handling of unknown or conflicting operations across epochs.
- [x] Specify profile hydration/admission interfaces, worker IPC request/reply
  framing and bounds, model ownership, queue reservations and cancellation.
- [x] Specify persistence ordering/receipt retention, retry/discard behavior,
  session invalidation and logout/reload/shutdown policies. Resolve how an
  explicitly discarded failed head operation unblocks subsequent queued writes.
- [x] Allocate module and fixture paths, configuration names and test resources
  to lanes. Define the async browser ABI used by I03/I09. Update the new contract
  record and current design/requirements to state approved consistency changes.
- [x] Gate: integration-ready types/codecs and behavioral contract fixtures pass;
  no production stubs or placeholder success paths. All agents use one version.
  Subsequent contract changes go through coordinator review and dependent retests.

### I03 — General asynchronous browser transport

- [x] Implement handle/completion-event APIs in `lib/std/web/fetch.bv` and
  `lib/glue/web/web.js`; preserve the existing synchronous ABI for compatibility.
- [x] Implement bounded responses, cancellation, timeout, cleanup, errors and
  completion ownership. Never pass a Promise through a String-returning WASM ABI.
- [x] Gate: browser/stdlib fixtures demonstrate continued painting during a slow
  request and no callbacks applied after release/logout. Existing APIs still pass.

**2026-10-23 implementation record (I03 complete):** the version-1
`http_async_*` ABI is exposed from `fetch.bv` and backed by a bounded browser
handle table. Promise values stay inside JavaScript; handles have monotonic
positive IDs, a 32-request cap, streamed UTF-8 bodies (1 MiB each / 32 MiB
retained aggregate), timeout, cancellation, release, event-once completion,
separate HTTP and transport status, and synchronous argument errors. The legacy
synchronous GET/method ABI remains in place. Non-streaming response bodies fail
closed because `arrayBuffer()` would allocate before enforcing the response
limit. The focused host fixture verifies a microtask paint while fetch is
pending, successful reads and repeat reads, HTTP 401 body/status, request
metadata, oversized-body failure, timeout, cancellation/release callback
suppression, and invalid options/method/URL/body handling. Documentation is in
`docs/architecture/portable-browser-stdlib.md` and the I02 ABI record.

Verification: `node tests/web_host_transport.mjs` passed. The Briev declaration
check passed once with `brievc check lib/std/web/fetch.bv`; a repeat invocation
was blocked by WSL `E_ACCESSDENIED` before the compiler launched. The browser
fixture runs under Node's host simulation; real generated-WASM/browser app
integration remains I09/I11 verification.

### I04 — In-memory profiles and pure admission state

- [x] Implement a standalone account-profile/admission module from I02's types;
  explicit inputs, no socket/SQL calls. All owner sessions share one profile.
- [x] Implement revision assignment, operation/payload deduplication, bounded
  reservations, rating upsert, persistence-status transitions and profile eviction.
- [x] Separate prediction publication from persistence confirmation; commit/failure
  transitions must not issue prediction actions or alter recommendation contents.
- [x] Gate: state-machine tests cover repeated edits, cross-owner isolation,
  duplicates/conflicts, overload-before-acceptance, stale results, cold-start
  counting, discard and pending-profile lifetime.

### I05 — Persistent process and IPC foundation

- [x] Implement reusable framed, bounded nonblocking parent-side IPC and complete
  child lifecycle. Define independent DB/prediction pool capacities.
- [x] Handle partial I/O, EOF, worker crash/hang, timeout/retry, restart, reaping,
  parent death and graceful shutdown. Close inherited descriptors correctly.
- [x] Implement/test immutable model-generation transfer and reader lifetime
  primitives agreed in I02; no live-model free while a worker still uses it.
- [x] Gate: dedicated real-process fixtures cover malformed frames, bounded
  memory, crash/restart and no zombies. Use test workers that
  exercise the real transport; do not wire dummy jobs as production success.

**2026-10-22 implementation record (I05 complete):** added bounded nonblocking
parent IPC, process lifecycle/supervision and immutable generation leases in
`examples/recommender/worker_io.bv` and `worker_lifecycle.bv`; added the real
SOCK_STREAM launcher, startup role/epoch handshake, child descriptor closure,
model image validation/acknowledgement and bounded retry helper in
`worker_pool.bv`. `model_snapshot.bv` now exposes validation of already-bounded
snapshot bytes, and `model_worker.bv` uses the shared parent-death and inherited
descriptor helpers. `worker_messages.bv` validates the `started` control reply.

The real-process fixture covers split startup frames, large partial writes,
bounded channel storage, pre-install prediction rejection, validated model
installation, honest `handler-unavailable` response, graceful shutdown/reap,
SIGKILL/restart eligibility and backoff, hung-worker timeout, malformed-frame
process isolation, and no zombies. The isolated model gate covers reader holds,
capacity refusal, reclamation and double-release rejection. Run with
`BRIEVC=/home/otto/briev-target/release/brievc bash tests/fixtures/recommender/run_worker.sh`.
All three gates and direct Briev checks passed. The fixture does not simulate a
descriptor-limit failure because the host's imposed fd-limit execution was
unreliable; socketpair failure is handled before child creation in the launcher.
Prediction and persistence job handlers remain explicit errors for I07/I08;
no dummy success is claimed. Fair owner scheduling and live pool integration
also remain with I08/I10.

**I05 prerequisite re-verification (2026-10-22):** all three gates pass with
exit code 0. Fixed `run_worker.sh` cleanup to remove its generated
`responsiveness_frame_gate` executable; temporary outputs are removed on success.

### I06 — Exact in-memory prediction without population rebuild

- [x] Use I01's stage evidence and a controlled Briev/generated-code experiment
  to test the overlay-copy/scratch-allocation hypothesis before optimizing.
- [x] Implement standalone active-profile evaluation over immutable CSR/means,
  with old owner snapshot row excluded, and reusable worker-local candidate scratch.
  Preserve formulas, observed unions, neighbor selection and deterministic ties.
- [x] Gate: finite-score/reference equivalence at small edge shapes and real
  dataset geometry; exact IDs/order and tolerance justified for Float arithmetic.
  Record same-geometry A/B timings. If evidence refutes the proposed optimization,
  record the result and provide the exact current engine through the agreed
  worker interface; do not invent a speedup or silently omit the prediction path.

**I06 current-compiler verification (2026-10-22):** edge, retained real-snapshot,
and bounded-reuse gates passed using compiler SHA-256
`63c8b9689c63af8a601509a278f086cfd52466d56aa52f37338c1552376ccaa2`. Every
finite score and ranked ID/order matched the reference at 0/4/5/20/100 ratings;
all three repeated full-shape pairs passed, including existing-owner exclusion.
The scratch reuse gate added one resident page. Interleaved engine ratios were
7.04x, 42.36x, 46.70x, 91.88x and 169.91x for 0/4/5/20/100 ratings. These are
engine microbenchmarks, not I16 browser/load claims. Results are preserved in
`benchmarks/results/recommender-i06-rerun-2026-10-22/`; see the I06 execution
record for exact error bounds and commands.

### I07 — Durable receipts and ordered persistence workers

- [x] Implement transactional operation receipts plus rating upsert using the
  existing Briev PostgreSQL client. Capture already-committed retries atomically.
- [x] Implement per-account FIFO ordering, independent account progress, bounded
  backoff/retry and explicit failed-head resolution using I04/I05 contracts.
- [x] Each worker owns its DB connection; return saved only after commit. Lost
  replies and ambiguous commit outcomes reconcile through receipts.
- [x] Gate: DB-backed tests cover duplicates, payload conflicts, receipt retention,
  rollback, lost acknowledgments, older retries, blocked head operations and
  independent accounts. No prediction callback is emitted by commit handling.

**I07 verification (2026-10-22):** the isolated
`tests/fixtures/recommender/run_operation_store.sh` gate passed against
`briev_recommender_test` using only schema `briev_recommender_i07`; its cleanup
removed that schema and its temporary binary. Checks passed for duplicate replay,
payload and timestamp conflicts, commit reconciliation on a fresh worker
connection, old retry protection, durable discard replay, transaction rollback,
receipt retention across an epoch change, worker commit acknowledgements, failed-head FIFO blocking,
independent-owner progress, retry timing/backoff and exhaustion. The shared
responsiveness contract gate also passed worker message validation and the 128
command/profile corpus. See `docs/plans/2026-10-22-recommender-i07-execution.md`.

### I08 — Prediction workers and scheduling

- [x] Connect I06's exact engine to I05's prediction pool. Bound one running and
  one latest pending prediction per owner, with fair scheduling between owners.
- [x] Tag results with epoch/revision/model generation, discard obsolete results
  and guarantee eventual current-result delivery once rating input settles.
- [x] Gate: real-worker tests cover coalescing, out-of-order results, worker death,
  model swaps, bounded scratch reuse and calculation while DB workers are blocked.

**2026-10-22 implementation record (I08 complete):**
`prediction_worker.bv` now validates the configured `lambda_milli` payload,
executes I06's exact reusable engine inside persistent prediction children,
and owns a bounded per-owner latest-pending queue with fair round-robin
dispatch. Dispatch rejects stale epochs, avoids workers already running another
job even if a readiness snapshot is stale, and selects a child with the matching
model generation. Completion checks the full issued tag, suppresses stale
successes/errors, clears terminal failures, and leaves newer pending work
dispatchable. Worker loss retries only current work, with a bounded attempt
count. Owner and worker capacities are explicit.

`model_generations.bv` holds a reader lease for each installed worker and each
running job. A worker acquires a new generation before releasing its previous
one; duplicate acknowledgements are idempotent. Job leases release against the
current registry, preserving intervening swaps. The four-generation limit
refuses a fifth live generation and permits reclamation after all relevant
readers move or release.

`worker_pool.bv` installs the exact engine only after snapshot validation and
successful workspace allocation, retains the old model until replacement is
ready, returns a full tagged recommendations event, and rejects mismatched
generation tags. The process gate predicts twice through the same worker-local
workspace and then swaps generation 1 to generation 2 and predicts again.
`lambda_milli` (0..1000, default 500) is now part of the version-1 `predict`
payload contract.

**I08 verification (2026-10-22):** `bash
tests/fixtures/recommender/run_prediction_workers.sh` passed queue fairness,
latest coalescing, stale result suppression, worker-loss retry, epoch rejection,
terminal error recovery, owner capacity, generation lease/capacity/reclamation,
worker message validation, persistent child prediction/reuse/model swap,
partial I/O, shutdown/reap, crash/restart, timeout, malformed-frame isolation,
and no-zombie checks. With
`RECOMMENDER_TEST_DATABASE_URL=postgresql://briev_test@127.0.0.1/briev_recommender_test`,
the live PostgreSQL advisory-lock probe confirmed
`prediction_completed_while_db_waiter_blocked=true`. The canonical I05
`run_worker.sh` regression runner also passed. I06's current-compiler reuse gate
measured one resident page after 100 repeated evaluations; the I08 process gate
also exercised repeated predictions through one child engine. No end-to-end
browser latency claim is made. Build logs/binaries are under the ignored
`target/recommender-I08/` directory.

### I09 — Browser state and optimistic interaction

- [x] Asynchronously migrate login, hydration, saves and reconnect in `app.rbv`.
  Use live submissions when available and async HTTP fallback with the SAME ID.
- [x] Paint pending feedback immediately, retain prior recommendations while
  calculating, and handle saved/unsaved/retry/discard states separately.
- [x] Remove POST-then-GET saves; reject stale/duplicate callbacks, patch changed
  rendered state, and make logout/reload with pending operations explicit.
- [x] Gate: browser fixtures using a controllable protocol peer cover both
  completion orders, delayed/failing saves, duplicates, cancellation and session
  change. Mock-peer success does not establish real end-to-end integration.

**2026-10-23 implementation record (I09 complete):** `app.rbv` now uses the
bounded async HTTP handles for login, registration, catalogue, profile hydration,
rating fallback, status reconciliation, retry/discard, logout and reconnect.
Live ratings paint optimistically under a stable operation ID; uncertain writes
are reconciled without automatic replay. Accepted/result/save events update
separate state, stale-session callbacks are ignored, predictions apply only at
the current revision, and save confirmations do not repaint recommendations.
Pending work produces a reload warning; logout first shows an explicit
confirmation and then cancels outstanding requests. Fixed the sequential-branch
logout bug found by the browser peer.

`browser_profile.bv` and `tests/fixtures/recommender/browser_pending_gate.bv`
cover optimistic ordering, failed/retry/discard transitions, same-ID retention,
duplicates and terminal-state ordering. The generated-app Playwright peer at
`tests/fixtures/recommender/browser_pending_peer.mjs` passes in Edge and covers
both recommendation/save completion orders, delayed async responses, HTTP
fallback, transport failure, cancellation, beforeunload and session-generation
changes. `tests/web_host_transport.mjs` also passes. `brievc check` passes for
the app and browser state module; the `--split` build emits app.wasm/app.html and
the generated page structure is valid. No live-server, database-blocking or
latency claim is made; those remain I10/I11/I15/I16.

Browser compilation exposed the UTF-8 byte-cursor defect in
`src/view_compiler.rs`; the cursor fix and a focused Rust regression are in the
working tree and recorded in BUGS.md. The existing WSL compiler predates that
Rust change. The human runs Cargo checks per WORKFLOW.md; see the final handoff
for the exact command. Static punctuation in this page stays ASCII until the
rebuilt compiler verifies the Unicode regression.

### I10 — Integrate independent server paths

- [x] Coordinator wires login/profile hydration, in-memory session validation,
  shared HTTP/WS admission and cached state reads into existing server modules.
- [x] Dispatch DB and prediction jobs independently after bounded admission;
  publish accepted/result/save-status events to the correct owner channels.
- [x] Remove hot-path account rereads, synchronous rating writes/calculation and
  commit-triggered recomputation. Hydration/receipt reconciliation use off-loop
  DB execution too; no blocking DB operation is moved into another reactor helper.
- [x] Gate: native real-HTTP/WS integration proves fresh recommendations arrive
  before a deliberately blocked rating transaction commits. Release lock: only
  save status changes. Existing auth/protocol validation stays intact.

### I11 — Integrate the real browser flow

- [x] Connect I09 to I10's real endpoints/channels; verify generated WASM and host
  artifacts match the tested source and browser URL.
- [x] Gate: real click -> pending paint -> fresh recommendation paint with DB
  blocked; separate saved confirmation after release; no save-follow-up GET,
  duplicate recommendation render or main-thread synchronous network stall.
- [x] Record early browser acceptance observations; reserve controlled timing for
  I16. Ownership: browser agent edits app files; coordinator edits server files.

**I10/I11 integration record (2026-10-25):** On branch
`integration/recommender-i10-i11`, built the native server and split WASM/host
artifacts from the same current sources with the release compiler. The real
Playwright gate `tests/fixtures/recommender/browser_live_server.mjs` passed at
`http://127.0.0.1:18110` against the isolated `briev_recommender_test` database.
It registered and hydrated an account with five ratings, opened the live
WebSocket, then held that account's PostgreSQL row lock while submitting a new
rating. Pending feedback painted immediately, the matching fresh recommendation
arrived before transaction commit, and the saved confirmation arrived after
commit. The browser observed 126 animation frames during the blocked write, no
main-thread long task (0 ms maximum), zero synchronous XHR, zero follow-up GETs,
and no recommendation DOM mutations or recommendation events after save. The
gate also checks that no duplicate HTTP submission occurs. Generated artifacts,
compiler build logs and server logs are retained under ignored
`target/recommender-i11-20261025/`.
The native server loop fixture also passes its real login/logout, fragmented
WebSocket rating, owner-isolation, ping/pong, HTTP admission, refresh/cache
agreement and cleanup assertions after correcting the fixture's close-frame
parsing and pong-frame selection.

The gate exposed a general keyed `b-each` host-renderer defect: unchanged nodes
were moved to the end of the container on every state flush, so a save-status
update caused remove/add DOM mutations despite no new recommendation result.
`src/glue/web_generator.rs` now reconciles keyed nodes in place and reorders only
when their position changes; its regression assertion covers the vector
renderer, and the live app exercises the collection renderer. The current
release compiler was rebuilt from this source before regenerating and passing
the browser gate. Exact compiler test suites remain subject to the user's
previous instruction to confirm Cargo tests separately.

### I12 — Integrate cache refresh and model generations

- [ ] Adapt `model_worker.bv` and shared state wiring to install complete models
  while keeping old generations alive for in-flight jobs. Rebase pending owner
  profiles without replacing them with older database ratings.
- [ ] Keep refresh periodic/explicit; commits do not trigger refresh/push.
  Installation does not unsolicitedly replace visible recommendations.
- [ ] Gate: refresh during writes/prediction, failed worker/artifact, generation
  retirement, self-neighbor exclusion and startup snapshot validation all pass.

### I13 — Recovery and lifecycle integration

- [ ] Integrate reconciliation after reconnect/server restart, unknown-operation
  conflict/resubmit, multi-tab state and lost commit acknowledgments.
- [ ] Integrate explicit retry/discard, failed persistence queue resolution,
  account deletion/revocation detection, idle eviction and orderly shutdown.
- [ ] Gate: current model/profile revision cannot move backward; pending writes
  are never represented as saved; memory-only crash loss is explicit; no stale
  operation silently overwrites newer persisted ratings after an epoch change.

### I14 — Native adversarial and resource gates

- [ ] Extend native/property tests for both job completion orders, SQL lock/error,
  rapid edits, two sessions/one owner and foreign owners, overload, partial IPC,
  worker failures, descriptor reuse and refresh/restart races.
- [ ] Run existing account/cache/server gates; replace obsolete write-before-
  predict assertions with approved semantics, retaining durability/isolation gates.
- [ ] Gate: full native evidence, bounded process/memory/FD counts, no leaked
  child processes and correct receipts/status/results in every tested schedule.

### I15 — Browser adversarial and rendering gates

- [ ] Exercise WebSocket and fallback, auth failures, slow network/DB, channel
  reconnect, two tabs, logout, retry/discard and rapid repeated edits.
- [ ] Assert save confirmations do not launch calculations or mutate recommendation
  DOM, input remains usable, and latest matching results render once.
- [ ] Gate: real-browser traces/screenshots and assertions, including narrow
  layout and existing registration/login/five-rating/reconnect regressions.

### I16 — Controlled performance acceptance

- [ ] Stop competing benchmark/build jobs, not the human's services. Run the
  plan's dataset/profile/concurrency/failure matrix with >=200 measured operations
  per workload, warmups and repeat runs. Check response correctness per sample.
- [ ] Report p50/p95/p99, throughput, CPU/RSS, errors, stage breakdown and first
  fifth-rating latency. Use browser-clock click-to-paint and server-clock stage
  durations separately. Run all compiler runtime benchmarks again and compare
  every row; preserve and label existing toolchain/environment limitations.
- [ ] Gate: p95 pending paint <=32 ms; single-user fresh result <=100 ms
  (<=50 ms stretch); 20 active owners <=250 ms; no app main-thread task >50 ms
  in tested flows; DB lock does not block prediction. Test 100 active owners and
  report capacity/tails without inventing an unapproved 100-user latency budget.
- [ ] If a target fails, trace/fix the cause through a separately owned task,
  rerun impacted correctness gates, then repeat measurements; do not mark complete
  using cached-GET timings or optimistic feedback as prediction latency.

### I17 — Final integration and handoff

- [ ] Run `cargo test --lib` and compare the exact accepted 38 failure names;
  build without new warnings; Praetor on changed directories. Run required
  safety/Kani, determinism and toolchain gates where the changed code requires them.
- [ ] Coordinator updates server/frontend/persistence architecture, current
  design/requirements/task progress, async API docs and BUGS.md in corresponding
  logical commits, preserving rationale. Historical records remain intact.
- [ ] Verify clean separation of compiler fixes, reusable stdlib APIs and app
  feature changes; prepare branch map and root PR-body drafts under WORKFLOW.
  Commit only intended files under the applicable commit workflow.
- [ ] Gate: reviewable end-to-end demo, blocked-DB trace, all-benchmark comparison,
  exact-reference results, failure-name comparison and remaining-risk statement.
  Report running services and pending operations. Do not assume push/PR authority.

## Claim / handoff record (coordinator-maintained)

| Task | State | Owner | Branch/worktree + base | Writable paths/resources | Evidence / next action |
| --- | --- | --- | --- | --- | --- |
| I01 | integrated/verified | Codex coordinator | recommender-proof-of-concept / shared checkout; 6fb27e01 baseline | trace.bv, server trace call sites, benchmarks/recommender_responsiveness, dedicated DB briev_recommender_i01, ports 18082/18083 | Full runtime/browser/native/stage evidence retained; exact 38-name library baseline; trace gates pass. See execution/results records. Owned services stopped. |
| I02 | integrated/verified | Codex coordinator | recommender-proof-of-concept; main-based compiler fixes isolated on codex/boolean-short-circuit, codex/print-traversal, codex/reflection-liveness, codex/event-trap-liveness and codex/wasm-const-width | portable protocol/admission records, native framing, fixtures, current specs and v1 architecture contract | Native command/event/worker, framing, trace and nested-print gates pass; generated WASM protocol page passes both epochs in Chrome. See contract architecture and benchmarks/results/recommender-i02/. |
| I04 | integrated/verified | Codex coordinator | recommender-proof-of-concept; current working tree | admission.bv, profile_state.bv, profile_admission_gate.bv; no DB | Standalone behavior gate passes; see I04 execution note. |
| I07 | integrated/verified | Codex coordinator | recommender-proof-of-concept; current working tree | operation_store.bv, persistence_worker.bv, I07-only database/schema and fixtures | I04/I05 gates passed; I07 DB, worker and scheduler gates pass. See I07 execution note. |
| I06 | integrated/verified | Codex coordinator | recommender-proof-of-concept; current working tree | active_profile.bv, prediction_scratch.bv; active_profile_* fixtures; retained I01 snapshot | Current compiler edge/full/reuse gates pass; exact same-geometry comparisons and timing record archived under recommender-i06-rerun-2026-10-22. |
| I08 | integrated/verified | Codex coordinator | recommender-proof-of-concept; current working tree | prediction_worker.bv, model_generations.bv, worker_pool child handler boundary; prediction_pool_* fixtures | Queue, generation, process, blocked-DB and I05 regression gates passed 2026-10-22. |
| I03 | integrated/verified | Codex coordinator | recommender-proof-of-concept; existing shared checkout | `fetch.bv`, `web.js`, `tests/web_host_transport.mjs`, portable-browser-stdlib docs | Node host behavior gate passes; Briev check passed once (repeat WSL blocked by E_ACCESSDENIED). Real app flow remains I09/I11. |
| I09 | integrated/verified | Codex coordinator | recommender-proof-of-concept; existing shared checkout | `app.rbv`, `browser_profile.bv`, `browser_pending_*`, browser event lifecycle; ports 18109/18209 unused | Generated WASM app and mocked Edge/Playwright browser gate pass; no real server integration claim. Compiler UTF-8 regression fix awaits human Cargo verification. |
| I10 | integrated/verified | Codex coordinator | `integration/recommender-i10-i11`; `e63b60f4` | server admission/workers; `browser_live_server.mjs`; isolated PostgreSQL row lock | Real native HTTP/WS app flow passes: prediction returned before locked rating commit; saved status followed commit. Evidence above; browser artifact hashes/logs under ignored target output. |
| I11 | integrated/verified | Codex coordinator | `integration/recommender-i10-i11`; `e63b60f4` | generated `app.wasm`/host, Playwright, native server on 18110, isolated DB | Real browser gate passes pending paint → fresh result during DB lock → saved after release; zero follow-up GET/sync XHR/duplicate submit; 126 frames; 0 ms max long task; no post-save recommendation DOM mutations. |
| I12–I17 | Unclaimed | — | — | — | Remain outside this assignment |

Allowed states: unclaimed, claimed, implementing, awaiting integration,
integrated/verified, blocked. Checkbox completion means integrated/verified, not
merely that an agent finished its branch. Record specific blockers/dependencies.

Each handoff supplies commit(s), exact changed paths, interface version, commands
and outputs, fixture/resource names, cleanup status, numerical/latency evidence,
documentation fragments and any required follow-up. Integration review checks
all upstream gates and downstream consumers before unlocking dependent tasks.
