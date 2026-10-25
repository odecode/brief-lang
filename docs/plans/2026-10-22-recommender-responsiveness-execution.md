# Responsiveness execution: I01 and I02

2026-10-22. Coordinator: Codex, single implementation lane. Authorized scope:
I01 baseline/instrumentation and I02 integration contracts only. No agents,
pushes or responsiveness optimizations are authorized here. The user subsequently
authorized database administration and service restarts; tests still use their
own DB/ports and terminate only verified test-owned processes.

Starting branch `recommender-proof-of-concept`, commit
`6fb27e0111af6460e7c8f2ff5042a8198e91911e`. Tracked tree clean; unrelated
untracked files (including the reviewed responsiveness plan and `.worktrees/`)
are preserved. Starting service inventory: PostgreSQL 12 on 5432,
`/tmp/briev-recommender-final/server`, Python static host on 8081. Never terminate
these as test cleanup. Existing compiler: `/home/otto/briev-target/release/brievc`.
Accepted failure names: `/tmp/briev-task12-failures-task13.txt` (38); copy the
exact set into persistent evidence before comparison.

## Work and verification order

1. Rebuild release from the starting sources, then run the existing complete
   runtime harness in an isolated archived checkout. Retain all rows and failures.
   Do not run compiler jobs during timing. Capture toolchain, binary hashes,
   machine, dataset and resource configuration.
2. Add opt-in bounded correlation/stage tracing without changing the current
   synchronous request topology. Measure real eligible profiles through native
   HTTP/live and browser click/render paths on a dedicated database and ports.
   Report absent pending feedback as absent, never as a measured optimistic paint.
3. Freeze version-one Briev codecs/types and behavioral fixtures, plus ownership,
   state transitions, endpoints, limits, ABI and lane allocation. I02 depends on
   the completed I01 gate; investigation can precede it.
4. Run native fixtures, browser gates, library failure-name comparison, build and
   directory Praetor. Update task progress only for verified gates.

Documentation: add a dated results record and versioned contract record; update
current requirements/design and application observability documentation. Preserve
historical plans and all existing rationale comments. No syntax/compiler/engine
algorithm changes are planned. Record any discovered defects in BUGS.md.

## Evidence

I01 baseline investigation is in progress. No optimization or I16 acceptance
claim is made. Application pilot tails use ten measured edits per profile;
the load probes use one simultaneous operation per eligible owner. These sample
counts identify stage/queue costs; they do not establish acceptance percentiles.

- Release build passed in 6m53s. Compiler SHA-256:
  `44696211356611b8ba9caadfafc8996aed0bcd5859bf1cf4e15457901215ac51`.
- The first private compiler-suite archive omitted two runtime build assets.
  That run is explicitly **incomplete**, preserved under
  `benchmarks/results/recommender-i01/runtime-incomplete-archive*`. The corrected
  runner copies/hashes both archives; a full rerun is in progress.
- User confirmed the dataset at `.kiro/specs/recommender-app/u.data` and authorized
  needed database administration/service restarts. Created only
  `briev_recommender_i01`, owned by existing role briev_test, with a scoped
  database/role/loopback trust rule. Other DB authentication is unchanged.
  Test DB duration logging is enabled. Its setup script refuses to reset a DB.
- Built native server and actual generated WASM/host assets for ports 18082/18083.
  Manifest: `benchmarks/results/recommender-i01/app-metadata.json`, including
  compiler/server/source/browser/dataset hashes and configuration. The persisted
  snapshot header verifies **943 users, 1682 items, 100000 ratings, zero account
  snapshot rows**; test profiles were separate overlays. Refresh was 86400 s.
- Initial browser warmups added movies; those artifacts remain diagnostic pilots
  under target/, not the fixed-geometry baseline. Corrected `geometry-*.json`
  preserves exact 4/5/20/100 sizes during measured edits, with a separate final
  new-rating operation. The initially empty profile becomes one rating. Every
  measured browser flow validates saved value, live receipt and rendered IDs.
- Server traces split DB calls, active_build, prediction scan, rank/release,
  push queue and dispatch. **active_build is an aggregate**: it includes copying,
  CSR/means and active PCC. I06 must measure its components and validate its
  optimization hypothesis; this evidence does not prove copying is the cause.
- A controlled write lock leaves both save and an unrelated catalogue read
  unfinished before release. The latter took 2232.93 ms in this single probe.
  A baseline-table read lock blocks only the refresh worker: a five-rating
  owner's save still completes. That test-created child was killed while
  blocked, then verified reaped, preserving the original model geometry.
- A separate protocol probe observed **four extended queries / twenty client
  protocol messages** for POST + GET. PostgreSQL's twelve Parse/Bind/Execute
  duration records sum to **2.201 ms**; the whole client flow was 1513.63 ms.
  SQL execution, protocol/socket wait, calculation and browser paint are distinct.
  No unsynchronized clocks are subtracted to claim network duration.
- Twenty active five-rating owners: 20 successful flows, zero errors, roughly
  25 s tail. One hundred active five-rating owners: 85 successful flows and
  15 client timeouts, with successful flows around 133–135 s. Timed-out writes
  have unknown client-visible outcomes; no automatic retry was issued.
- Native single-profile phase RSS grew from 2,386,890,752 to 2,605,387,776 bytes.
  After the complete exploratory sequence, the test server reached about 4.7 GB.
  This is observed residency growth, **not an isolated/proven leak diagnosis**.
  I04–I06/I14 must enforce ownership/physical resource bounds and plateau gates.
- Both I01-owned app services were stopped after application measurements and
  before compiler timing, releasing that residency. PostgreSQL remains running;
  the original browser database and its data were not reset.
- Native trace gate passes with tracing disabled/enabled, including hostile ID
  rejection and an invalid clock ID. Expanded timestamp-failure propagation
  cases will run with final gates. The clock guard is an application fix only;
  it does not alter the prediction algorithm. I02 subsequently exposed the
  separate compiler correctness prerequisite recorded below.

Sources served for measurements are pinned by the manifest's source hashes and
diff. Subsequent diagnostic-context clearing and timestamp failure propagation
guards affect only background attribution/clock errors; final native gates build
the final sources. No successful measurement observed a clock error or installed
a replacement model.

## I02 interface freeze and compiler prerequisite

The versioned architecture record is
`docs/architecture/applications/recommender-responsiveness-contract-v1.md`.
Portable Briev modules implement strict bounded JSON, exact textual counters,
operation identity, five event types, twenty worker message kinds, stale-tag
checks and the persistence retry/uncertainty/discard transition table. Native
framing handles BRV1 headers, partial prefixes, bounds and adjacent frames.
Admission records specify committed/accepted profiles, reservations and effects;
the admission implementation remains I04. Browser/server typed JSON extraction
now shares those helpers. No asynchronous production cutover is claimed.

The first native event fixture trapped at `idx > 0 && items[idx-1]...`: LLVM
emitted the invalid RHS read eagerly. This is a compiler defect, not an app
algorithm issue. A main-based managed worktree on `codex/boolean-short-circuit`
isolates the general CFG lowering and regression tests. Its plan records the
IR evidence and interpreter agreement. Conditional RHS assignments additionally
required expression-block local discovery and native entry slots for mutable
ABI parameters. The application will integrate only that focused fix, preserving
its existing compiler prerequisites; no unrelated main changes are merged.

Pre-change application `cargo test --lib`: **3178 passed / 38 failed**, exact
failure-name set identical to `accepted-library-failures.txt`, 703.95 seconds.
Compiler prerequisite and final native/WASM/build/Praetor gates are pending.

The logical fix is isolated at codex/boolean-short-circuit (0af7ae7f), integrated
as 5b9ac7f8. The application checkout predates main's canonical/state pointer
caches; its emitter scopes last-value entries without introducing those caches.
This compatibility adaptation is separate from the main-based fix's semantics.

Native trace gates pass in the integration compiler with tracing both off/on,
including timestamp failure propagation. The worker fixture's foreach/guard
failure diagnostic then exposed the print plugin's partial traversal. The
separate codex/print-traversal branch adds a general exhaustive mutable postorder
visitor and removes obsolete print-only partial walkers/type tables. Focused
print/LLVM-print tests: 14 passed; mutable-visitor tests: 2 passed; cargo check
completed without warnings. The touched print/read-visitor bases were verified
byte-identical between the app and fix branch before focused integration copies.
The combined application library run is the final failure-name gate. An earlier
integration attempt failed to compile against absent pointer-cache fields, then
an intermediate library run was deliberately interrupted after the independent
print prerequisite was found; neither is represented as a passing final gate.

## I05 implementation record (2026-10-22; complete)

The user authorized I05 after I02 integration. The new native-only
`examples/recommender/worker_io.bv` keeps BRV1 partial-write offsets, advances
one nonblocking `send`/`recv` per poll step, uses `MSG_NOSIGNAL`, and caps the
retained receive allocation at one maximum frame. Taking a complete frame
returns the updated channel with any buffered suffix preserved. The shared
codec remains the only frame parser/encoder.

`worker_lifecycle.bv` defines separate bounded persistence/prediction worker
counts, parent-death signaling with a post-`prctl` parent check, closure of
caller-specified inherited descriptors, nonblocking `wait4` observation,
timeout kill/reap, bounded restart eligibility, and a four-slot immutable
model-generation registry. Reader-held generations cannot be reclaimed.
`worker_pool.bv` adds persistent socketpair launch, child setup, startup
role/epoch acknowledgement, strict bounded frame handling, validated model
image installation and restart backoff. `model_snapshot.bv` validates bounded
in-memory image bytes; `model_worker.bv` uses the shared child guard.

The isolated gate command is
`BRIEVC=/home/otto/briev-target/release/brievc bash tests/fixtures/recommender/run_worker.sh`.
It passed the model lease gate, process gate, and frame gate. The process gate
observed a split startup read, forced a large partial write, checked receive
capacity, rejected prediction before installation, validated and acknowledged
an installed model, and verified the explicit `handler-unavailable` error for
prediction work (the real handler belongs to I08). It also verified graceful
shutdown, child reaping, SIGKILL detection/restart eligibility/backoff,
timeout kill/reap, malformed-frame process isolation, and no zombies. Direct
Briev checks passed for the changed language files and fixtures. The existing
host linker emitted its target-triple warning. A host fd-limit runtime test was
unreliable and is not claimed; launcher socketpair failures are handled before
child creation. Owner fairness/live pool integration remains I08/I10. Praetor
was unavailable in this environment (`praetor` command not found).
