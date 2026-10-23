# Recommender: independent in-memory prediction and asynchronous persistence

2026-10-22. Status: **DRAFT FOR HUMAN REVIEW; implementation not started.**
This document is the handoff for a fresh session. The current request authorizes
writing this plan, not implementing it. Review and iterate with the human first.
Record implementation evidence in a new dated execution record; preserve this
reviewed design and earlier historical records.

## 1. Outcome and human decisions

Reduce time from clicking Save rating to the browser painting recommendations,
and keep input responsive throughout. The engine must calculate from accepted
in-memory ratings independently of the PostgreSQL transaction. A slow or failed
write must not hold up prediction. PostgreSQL stores durable ratings and supplies
future population/cache rebuilds; it is not the per-prediction source of truth.

The human explicitly accepts recommendations based on a slightly stale shared
model or a rating that has not yet committed. A database completion must **not**
recalculate or replace the visible recommendation set. Confirm persistence
separately. Algorithm correctness, account isolation, and save-status honesty
remain required; relaxed model freshness does not permit arbitrary scores.

Recommended flow:

```text
Click Save
  -> browser immediately paints rating as pending
  -> asynchronous submission over the live channel (async HTTP fallback)
  -> reactor validates identity, bounds, deduplication and queue capacity
  -> assign account revision and update the in-memory profile
       |-> prediction worker -> recommendations(revision) -> browser paint
       |-> persistence worker -> PostgreSQL commit -> saved(operation) -> status only
```

Neither branch waits for the other. Their completion order is unrestricted.
"Accepted" means retained in server memory; "saved" means database commit
confirmed. Do not show "saved" upon queue admission or optimistic display.

## 2. Fresh-session orientation and scope

Workspace: `C:\Users\wotto\code\briev-lang`; WSL source path:
`/mnt/c/Users/wotto/code/briev-lang`. Observed branch:
`recommender-proof-of-concept` (renamed from `integration/ptr-provenance` on
2026-10-22), HEAD `6fb27e01`. Recheck both before work.
The tree contains many unrelated untracked files and `.worktrees/`; preserve
them. Never restore/reset files or stage the entire tree.

Read, in order:

1. `AGENTS.md`, `docs/plans/INDEX.md`, `docs/handoff-methodology.md`.
2. `.kiro/specs/recommender-app/WORKFLOW.md`, `requirements.md`, `design.md`,
   `tasks.md` (including START HERE and final handoff).
3. This plan, `docs/architecture/applications/recommender-server.md`,
   `recommender-frontend.md`, `recommender-persistence.md`, and
   `recommender-accounts.md` in that same directory.
4. `docs/plans/2026-10-21-recommender-cache-reuse.md`,
   `2026-10-21-recommender-frontend.md`, and `2026-10-21-backend-checkpoint.md`.

Session override from the human: the agent executes **all** cargo/brievc and
other necessary commands itself. This supersedes WORKFLOW's command-execution
split for this effort. Keep meaningful progress/teaching notes and focused
increments. Follow its clean compiler/stdlib/app branch separation and fork-only
push policy; do not push main/integration or open/merge PRs without authorization.
This draft does not authorize implementation, pushes, or changes to services.

Keep production application, protocol and engine logic in Briev. Reusable
browser API adapters may live in the existing JavaScript host module, exposed
through the Briev stdlib. Rust changes are for demonstrated general compiler
gaps only, with their own repros/tests/branches. The PostgreSQL client is already
native Briev (`lib/std/db/pg.bv`), **not libpq/C FFI**; the earlier chat description
of that boundary was incorrect. Do not introduce a Python/Node application server
or database worker. Existing Python static hosting is development infrastructure.

Do not expand this work into unrelated optional tasks. The performance and
failure tests below are required verification for this architecture regardless
of older task-16 optional labels. Leave the 38 explicitly accepted environmental
library-test failures alone; compare names, not just totals.

## 3. Verified current path and misleading earlier measurements

| Source | Current behavior / consequence |
| --- | --- |
| `examples/recommender/app.rbv:save_rating`, `client_load_state` | Blocking POST, then blocking GET /state, then update UI. |
| `lib/glue/web/web.js:fetch_method`, generated `target/recommender-web/app.mjs` | Synchronous XHR freezes the browser main thread. Edit authored sources, never generated output. |
| `server_api.bv:api_rate` | Reads account from DB and performs synchronous rating upsert. |
| `server_state.bv:server_after_reply`, `server_update_owner` | Reads DB again, computes owner recommendations, then queues push on the reactor thread. |
| `server_state.bv:server_cached_state` | GET authenticates/loads ratings from DB and reads materialized owner recommendations; it does not time fresh calculation. |
| `server_model.bv:active_build` | Copies population into a temporary overlay, builds CSR/means and computes active similarities. |
| `server_model.bv:active_user_prediction`, `active_item_prediction` | Allocate candidate scratch buffers repeatedly across catalog items. |
| `server_state.bv`, `model_worker.bv` | Shared model refresh already runs in a forked worker; install and owner-view recalculation still do work between poll sweeps. |

Earlier observations are provisional, not an acceptance baseline:

| Observation | Value | Limit |
| --- | ---: | --- |
| GET /recommendations, ten sequential calls | ~43–48 ms | Cached view; includes DB/network/client overhead, excludes browser paint. |
| First four POST /rating calls | ~135–140 ms | Below five-rating threshold; excludes subsequent GET and paint. |
| Fifth POST /rating | ~963 ms | First non-cold recommendation computation; no traced breakdown. **No evidence of a fifth-rating full-model refresh threshold.** |
| 100 GETs with 20 client threads | ~880 ms median | Test account had ZERO ratings; cold-start responses, not prediction throughput. Queueing cause not isolated. |
| Runtime harness `recommender` | 10.5 ms | Entire unrelated benchmark workload; neither one production prediction nor a production recommendation request. |
| Full model cold build / warm startup | ~12–15 s / 0.40–0.47 s | Historical development observations, separate from per-owner latency. |

Do not reuse those numbers as guarantees or derive a prediction speedup from
them. The chat's earlier claims attributing all delay to single-thread scheduling
or the fifth rating to a full refresh were not established. Investigate database
protocol waits, socket behavior, computation, queueing, and rendering separately.

## 4. State, messages, and consistency contract

### In-memory account profiles

Load identity and persisted ratings at login/session hydration. Thereafter use
an account-owned profile keyed by stable account ID, not database row position.
All that owner's sessions share the profile. Keep identity/session generation,
accepted revision, current ratings, per-operation persistence status, and latest
recommendation revision/model generation. No DB query on every authenticated
rating, cached recommendation read, or push; retain existing opaque-session
validation in memory. Define account revocation/deletion policy explicitly:
session termination on detected deletion, with bounded reconciliation at login
and refresh; do not claim immediate external-DB revocation with cached identity.

Revision is assigned by the reactor and monotonic within a server epoch. A
client operation ID is stable across retries; connection slot/FD is never an
identity. Workers and clients compare `(server_epoch, account_id, revision,
model_generation)` as appropriate. Never publish another account's result or
apply an old result over a newer accepted profile. Model generation alone must
not reset the account's rating revision.

### Wire events and retries

Extend HTTP and WebSocket adapters over ONE admission service:

- Submit: client operation ID, item ID, rating; owner comes from authenticated
  session/channel. Never accept a frame's claimed account as authority.
- Accepted: operation ID and assigned revision, plus authoritative rating delta.
- Recommendations: revision, model generation, cold-start flag or ranked items.
- Saved: operation ID/revision after commit. Changes save indicators only.
- Save failed: operation ID, retryability and actionable message. Preserve rating
  and displayed recommendations; mark unsaved and allow retry/discard explicitly.

Reserve bounded queue/profile capacity BEFORE accepting. If full, reject clearly;
browser optimistic state becomes unsent/retryable. Repeat operation with identical
payload returns its original revision/status; same ID with different payload is
an error. A lost reply does not imply a failed commit. Add a durable operation
receipt keyed by account + operation ID in the rating transaction so reconnect/
retry can distinguish already-committed work. Bound in-memory receipt retention;
define durable receipt retention without breaking the supported retry window.

### Ordering and failure policy

Accepted writes persist in order per account, including repeated edits of one
item; different accounts may run concurrently. A retry of an older edit must
never overwrite a later saved edit. Start with per-account FIFO persistence,
idempotent transactional receipts, and bounded retry/backoff; a failed operation
holds that account's subsequent durable writes pending until retry or explicit
resolution. It does not block prediction or other accounts. Do not silently
drop accepted writes or coalesce durable operations unless the receipt semantics
for every superseded operation are specified and tested.

Pending state is memory-only initially. A process crash before commit can lose
an accepted rating; this is the selected low-complexity tradeoff, disclosed by
the pending status. "Saved" remains durable. Do not add a separate durable queue
in this phase. Browser retains unresolved operations across transient reconnects
within the page session and reconciles receipts after a server restart; never
auto-replay stale operations over newer persisted edits. Specify an explicit
conflict/resubmit path for unknown operations across epochs. Page reload/logout
must not silently claim pending ratings are saved; show unresolved-save status
and provide a deliberate leave/retry action. Disk persistence of browser queues
is a separate privacy/lifecycle decision, not an implicit implementation detail.

Persistence failure does not automatically roll back the recommendation display.
A user-requested discard changes the in-memory profile and may trigger a new
prediction; commit notification alone never does. Fully committed, idle profiles
may be evicted; pending/in-flight state must stay owned until resolved or an
explicit shutdown policy reports it. Bound accounts, ratings, queues and results.

## 5. Execution architecture

### Browser

Add a general asynchronous request handle/completion-event API to
`lib/std/web/fetch.bv` and `lib/glue/web/web.js`, following existing WebSocket
event ownership. Do not return a JavaScript Promise through a synchronous
String-returning WASM ABI. Preserve existing sync APIs for compatibility; migrate
this app's login/load/save paths. Support cancellation, timeout, bounded response
size, cleanup and stale callback rejection after logout or session change.

Prefer the existing live channel for saves once ready. Use async HTTP fallback
with the same operation ID if the channel is unavailable; retry must not create
a second logical save. Remove POST-then-GET from the save path. Hydration and
reconnect fetch authoritative state asynchronously. Update the edited rating
immediately as pending; preserve the previous recommendations while calculating.
Apply a matching new set once; deduplicate HTTP/WS delivery. Patch changed DOM
state rather than replacing the whole ratings/recommendations subtree. Ensure
paint occurs before network completion; setting a variable in a blocking txn
does not achieve optimistic feedback.

### Reactor and workers

The reactor owns sessions, account profiles, revision assignment and publication.
It performs bounded admission/IPC/socket work, not blocking DB I/O or prediction.
Use bounded, persistent Briev worker processes as the initial execution model,
consistent with the app's Linux target. Separate persistence and prediction pools
so a database lock cannot consume every prediction worker. Size both explicitly
with configuration and account-ordering constraints; no unbounded fork per click.

Each persistence worker owns its own PostgreSQL connection. Each prediction job
uses an immutable model snapshot plus copied small owner profile. Communication
uses framed, bounded IPC with partial-read/write handling and job IDs. Workers
must not call pg_close on the reactor's inherited connection or retain its socket
descriptors; preserve the existing raw-close/parent-death/reaping rationale.
Persistent workers imply explicit shutdown, timeouts, crash restart, job retry,
and model-generation distribution; implement these together, not as stubs.

Coalesce **prediction** jobs per account to the latest revision: at most one
running and one latest pending job. Do not add an arbitrary UI debounce initially.
Discard obsolete results. If a stream of edits outpaces computation, publish the
latest completed result only if its revision is still current; show calculating
and guarantee eventual publication once input settles. Queue bounds and fairness
must prevent one user starving others.

### Prediction data path and refresh

Use current in-memory ratings with the immutable shared population/item cache.
Exclude the owner's old snapshot row to prevent self-neighbor duplication.
First measure `active_build`/prediction stage costs; then remove whole-population
copy/rebuild via an active-profile view over existing CSR/means. Reuse per-worker
scratch for candidates and top-K aggregation. Preserve equations, observed-union
semantics, tie order, cold-start threshold and finite score checks. Compare the
new view against the current calculation using identical profiles and model.
No approximate-neighbor algorithm or compiler vocabulary recognition is needed.

PostgreSQL commits advance the existing durable population revision. Cache
refresh remains periodic/explicit and uses committed DB state. A pending profile
stays an overlay across refresh, never replaced by an older database version.
Do not start a model rebuild or recommendation push on each commit. Install a
complete new model generation safely, keeping old generations alive until all
readers finish. Let current visible recommendations stay until the next rating
or explicit recommendation refresh; installing a cache need not push a second
set unsolicited. New jobs use the new generation. Rebase worker ownership and
profile hydration without dropping pending edits or resurrecting old ratings.
Startup snapshot validation/revision rules remain intact.

## 6. Measurement before implementation

First create a reproducible benchmark and a NEW dated baseline record on the
actual starting commit. This draft intentionally does not start load tests or
claim a clean baseline. Before performance code changes, run a clean release
build and `bash benchmarks/build_and_bench.sh --runtime`; record ALL benchmark
rows before/after, including failures, per AGENTS.md. The historical 41-entry
ledger `benchmarks/results/2026-10-22-cache-integration.md` is context only.

Add a production-path browser/HTTP/WS harness under the repository benchmark
system, with operation IDs and monotonic stage timestamps. A host-side driver
may orchestrate measurements; all production behavior remains Briev. Browser
click-to-paint uses one browser clock (DOM mutation plus animation-frame/paint
evidence). Server stage durations use its monotonic clock; never subtract
unsynchronized browser/server timestamps to invent a network duration.

Required stages: click/input feedback, submit, admission, prediction queue/start/
end, result receive/render, persistence queue/start/commit, save-status render.
Record browser long tasks, HTTP OPTIONS/preflight, DB query count/time and full
flow topology. Test real 943-user/1682-item/100000-rating baseline with separate
test accounts having 0, 4, 5, 20 and 100 ratings; existing edits and new ratings;
warm/cold profile; model refresh in progress; deliberately blocked DB writes;
1, 20 and 100 simultaneously active accounts. Distinguish idle socket capacity
from active throughput. Use isolated test DBs, not the human's browser account.

Record p50/p95/p99, sample count, warmups, throughput, CPU/RSS and errors, along
with commit, compiler, dataset, machine, client location and server config. Check
response content, revision and save status for every sample. Interleave baseline
and candidate runs on the same geometry/config without competing cargo jobs.
Before each optimization validate its hypothesis through actual generated IR
and linked binary when it is a codegen claim, or a controlled Briev/protocol
experiment when it is an architecture claim. Refuted hypotheses block that fix.

Proposed local acceptance budgets (reviewable targets, **not measured promises**):

| Metric | Single active user | Load/failure expectation |
| --- | --- | --- |
| Click to pending-rating paint | p95 <= 32 ms | Remains responsive during DB lock/refresh |
| Click to fresh recommendation paint, warm model | p95 <= 100 ms; stretch <= 50 ms | 20 active accounts: p95 <= 250 ms |
| Save status | Prompt after commit | DB lock: visibly pending, prediction proceeds |
| Main-thread work per event | No app-generated task > 50 ms in tested flows | No synchronous network wait |

Use at least 200 measured operations per workload after warmup and sufficient
repeats to assess tails; disclose when p99 is statistically weak. Report first
eligible fifth-rating latency separately. If targets fail, document the traced
remaining cause and resolve it within this responsiveness work; don't relabel a
cached GET or optimistic rating paint as fresh recommendation latency.

## 7. Implementation sequence after review

1. **Baseline/instrumentation:** reproduce browser clunkiness; add correlation
   and correct production-path harness; capture full compiler benchmark baseline.
   Establish actual computation vs DB/network/render costs before choosing pool
   sizes or claiming a speedup. Document any newly found defects in BUGS.md.
2. **Async browser foundation:** implement/test reusable async host/stdlib API;
   migrate app requests, pending/save-failure states and session cleanup. Deliver
   measured immediate feedback without claiming prediction independence yet.
3. **In-memory profiles and admission:** share authenticated profiles across
   sessions; add epoch/revisions, operation receipts, bounded queues and unified
   HTTP/WS protocol. Add persistence ordering and failure semantics together.
4. **Independent workers:** dispatch prediction and persistence at admission;
   implement complete IPC/process lifecycle, ownership, overload handling and
   stale-result filtering. Prove recommendation delivery while DB commit is
   blocked. Remove follow-up GET and commit-triggered recalculation.
5. **Measured engine work:** implement overlay-free active-profile evaluation
   and reusable scratch if the stage baseline confirms the cost; exact reference
   gates and generated-code A/B first. Tune worker counts from evidence.
6. **Refresh/recovery integration:** generation-safe models, pending overlays,
   reconnect/lost acknowledgments, process restart and shutdown behavior.
7. **Final verification/documentation:** run the matrix below, full before/after
   benchmark tables, browser review, update architecture/spec/task status, and
   prepare focused carve-outs/PR-body drafts under the established workflow.

Each phase must leave a working, tested increment, with honest interim behavior.
No committed stubs or silent success on unimplemented paths. Keep the human
updated on observed behavior, how it works and why the tradeoff was chosen.

## 8. Required correctness and failure gates

- Same model/profile produces reference-equivalent finite scores, item IDs and
  deterministic order; rated items excluded; fewer than five distinct ratings
  remains cold; updating a rating does not increase distinct count.
- Hold a PostgreSQL rating transaction behind a lock: accepted rating appears,
  fresh recommendations render, save remains pending. Release it: saved status
  changes exactly once, **no new prediction job or recommendation DOM update**.
- Force permanent write failure: prediction still arrives; unsaved status/retry
  remains truthful; other accounts continue. Retry cannot overwrite newer edits.
- Two tabs on one account, another account, rapid same-item edits, reordered
  worker completions, duplicate HTTP/WS delivery, lost commit acknowledgments,
  reconnect and server-epoch changes preserve ordering and ownership.
- Refresh during pending writes/computation; old model stays alive for readers,
  new jobs use new generation, old results cannot overwrite current profiles.
- Queue saturation rejects before acceptance; bound memory, IPC payloads, worker
  count and output. Worker crash/hang, partial IPC, peer close, logout and process
  shutdown have tested cleanup/retry paths; no leaked descriptors or zombies.
- Browser continues accepting input and painting during slow DB/network/worker
  operations. Timeout/cancel/auth failures retain clear, accurate UI state.
- Run existing native cache, account and server runners plus browser regressions;
  update write-before-predict tests to the reviewed new contract rather than
  weakening validation, isolation or durability tests.
- `cargo test --lib`: compare exact failure-name set to accepted 38; cargo build
  with no new warnings; Praetor on changed DIRECTORIES, no new diagnostics in
  changed files. Run applicable safety/Kani gates and full LLVM determinism/
  toolchain gates if backend changes are necessary. Do not fix accepted
  environment failures as a side project.

## 9. Useful commands and operational precautions

From WSL, source remains the Windows tree; use Linux cargo target storage:

```bash
cd /mnt/c/Users/wotto/code/briev-lang
source ~/.cargo/env
export CARGO_TARGET_DIR="$HOME/briev-target"
cargo build --release
cargo test --lib
bash benchmarks/build_and_bench.sh --runtime
```

Build native server and browser independently:

```bash
~/briev-target/release/brievc build examples/recommender/server.bv --out /tmp/briev-responsive-server
PATH="/usr/lib/llvm-17/bin:$PATH" ~/briev-target/release/brievc build examples/recommender/app.rbv --split --out target/recommender-web
```

Existing fixtures (dedicated DB only; do not run schema-resetting copies
concurrently): set BRIEVC, PGUSER and PGDATABASE explicitly, then execute
`tests/fixtures/recommender/run.sh`, `run_accounts.sh`, `run_server.sh`,
and `run_cache.sh` with bash. Read each runner's parameters/cleanup first.

Last observed services: backend `/tmp/briev-recommender-final/server` on 8080,
static frontend on 8081, PostgreSQL on 5432; browser DB
`briev_recommender_browser_task14`, PGUSER `briev_test`, refresh interval 3600 s,
source `.kiro/specs/recommender-app/u.data`. These are historical observations,
not a current health check. Inspect processes/ports first. Prefer isolated ports,
schemas/database and CACHE_PATH for benchmarks; never reset the browser DB or
kill the human's services to collect measurements. Verify which binary/generated
frontend is actually served so stale artifacts do not invalidate the test.

## 10. Documentation and review decisions

Update the application server/frontend/persistence architecture documents in the
same implementation commits as their contracts. Document reusable async API in
the stdlib/web architecture location found during implementation. Preserve and
rewrite existing rationale with when/why/pattern/retirement information. Update
recommender requirements/design to replace strict write-before-predict semantics
explicitly, and link execution evidence from tasks.md; historical reports stay
unchanged. Syntax/compiler changes, if unavoidable, require corresponding spec,
tutorial and highlighter maintenance per AGENTS.md.

Design choices proposed for approval with this plan: memory-only pending queue
with durable confirmation, no automatic recommendation rollback on write failure,
per-account ordered persistence, coalesced latest-profile prediction, separate
bounded process pools, and no unsolicited rerender upon commit/cache installation.
Review especially the crash-before-commit tradeoff and proposed latency budgets.
A durable intake log, approximate neighbors, a new web framework, multiple app
servers, and a production-grade admin/auth redesign are not required here.

Implementation completion evidence must include measured click-to-paint results,
the blocked-DB demonstration, exact reference gates, final branch/commit map,
test-name comparison, all-benchmark ledger, and a truthful remaining-risk list.
