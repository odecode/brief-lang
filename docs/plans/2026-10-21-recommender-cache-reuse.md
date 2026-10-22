# Recommender cache reuse and nonblocking refresh

2026-10-21. Authorized after the task-14 browser work; that uncommitted work
is preserved. Implement exact intermediate reuse, durable startup reuse, and
off-loop refresh. No approximation, optional tasks, or environment-failure fixes.

## Evidence and hypothesis

`cf_engine.bv` imputation calls base PCC for each missing cell, and final PCC
calls imputation again for every pair's union key. Memoizing base pairs and
each orientation's imputed cells removes repeated work without changing the
equations, neighbor order, or pair-specific observed union. Symmetric base
reuse must be compared numerically against the direct engine before adoption.
`server_model.bv:model_load` always builds, passing zero as source revision.
`server_state.bv:server_refresh` synchronously builds in the poll thread.

## Baseline and pre-implementation experiment

The original full-data process was stopped on explicit user instruction after
more than 37 minutes without readiness (100,000 records, 943 users, 1,682 items;
~one CPU, ~2.3 GiB resident). This is a censored startup measurement, not a
completed benchmark or a speedup claim. Save the current engine before editing;
run direct and prepared variants on identical deterministic sparse populations,
compare every matrix entry including empty/constant rows, and interleave runs.
Run clean release build plus the full runtime benchmark harness before and
after; record every verdict, including toolchain/environment failures. The
application-only change must not teach algorithm recognition to the compiler.

## Implementation

1. Prepare base user/item matrices and separate imputed user/item tables;
   evaluate final PCC over the ORIGINAL sparse union; release scratch storage.
2. Snapshot a transactionally maintained DB revision with accounts/ratings;
   validate a versioned, database-specific persisted image from one read;
   write a unique temporary artifact and atomically rename only on success.
   Reject stale/corrupt/partial images and preserve the old artifact on failure.
3. Fork a native Linux worker without sharing the PostgreSQL connection;
   capture the immutable population before computation, close inherited network
   descriptors, build/write the replacement there, reap using nonblocking wait,
   and install only validated complete snapshots between poll sweeps. Keep
   serving the old snapshot and retain it on any failure. Queue refreshes that
   arrive during an active build. Never run the reactor in the child.

## Verification and documentation

Exact-reference matrix gates and same-geometry timings; startup reuse/edit/
delete/truncate invalidation; corruption/write-failure gates; HTTP responsiveness
during refresh, worker failure, queued refresh and reaping; native server gates;
browser regressions; `cargo test --lib` compared to the accepted 38 failures,
build, Praetor changed directories and required LLVM determinism gates. Update
application architecture docs and BUGS.md for discovered defects, preserving
existing rationale and adding dated replacement/undo explanations. No committed
stubs. Commit and push clean compiler/stdlib/application branches as applicable.

## Results

Pending measurements and implementation.

### Exact reuse experiment and lifecycle gates

The additive `cf_prepared.bv` variant was compared against the untouched direct
engine BEFORE wiring it into model_load. Complete user/item matrices agree within
1e-6 on deterministic sparse fixtures with empty and constant rows; NaNs fail
the comparison. A 241x241 fixture (13,403 ratings) interleaved direct/prepared
executables using the same generated LLVM/link pipeline: direct 127.16, 116.49,
88.11 s; prepared 0.12, 0.06, 0.09 s. These development timings are provisional:
concurrent compiler checks contend for CPU. The checked sample was identical
(0.405068398); complete-entry equivalence is a separate small-shape gate.

Full MovieLens geometry (943 users, 1,682 movies, 100,000 ratings), same binary,
configuration and database, interleaved cold/warm starts, readiness = successful
OPTIONS HTTP response; each run additionally checks six user and six item pairs
against the direct engine at THAT geometry. All six reference gates passed.

| Run | Cold build to readiness | Fresh persisted startup | Artifact bytes |
| --- | ---: | ---: | ---: |
| 1 | 11.797 s | 0.400 s | 33,010,161 |
| 2 | 11.863 s | 0.445 s | 33,010,161 |
| 3 | 15.288 s | 0.473 s | 33,010,161 |

These are application startup observations under concurrent verification, not
isolated compiler benchmark ratios. The old run was censored beyond 37 minutes;
there is no completed same-geometry original-runtime number to divide by.

The native snapshot gate passes round-trip numerical equivalence, cache reuse
while the source table is unavailable, same-count edit invalidation, checksum
corruption, truncation, write failure, HTTP response while the refresh worker is
blocked on a DB lock, queued refresh, completed installation, killed-worker
retention, rollback/delete/TRUNCATE/account changes, and revision-table recreation.
The fd lifecycle gate passes 512 reads under a 64-descriptor process limit.

The first round trip exposed an outdated layout assumption: Matrix/Vector reserve
eight bytes per Float but typed indexing uses the declared four-byte Float width.
Encoding now copies the live prefix and zeroes spare capacity. Magic 2026102102
pins this canonical native format. No recommendations or arithmetic were changed.

## Final verification (2026-10-22)

The final full library run completed: 3178 passed, 38 failed, 743.48 seconds.
The failure-name set exactly matches the accepted task-13 baseline: no added
or removed failures. Both new lexical-scope regressions pass. Final release
build completed without new warnings, and its backend/browser artifacts built
successfully. The release frontend boots at localhost:8081 without page errors;
native backend OPTIONS and frontend HTML return HTTP 200. Compiler, stdlib,
cache and required frontend gates are complete; optional task 14.4 is skipped.

## Runtime harness closure (2026-10-22)

The release runtime harness reached all 41 recorded entries before the same
final shell CRLF failure as the baseline. Numeric timed-program correctness
checks match. Existing limitations remain: nbody_newton_accel pthread linking,
bridge_glue Python-host segfault, missing WSL Node, and nested shell CRLF.
The complete before/after table is benchmarks/results/2026-10-22-cache-integration.md.
Timings are provisional concurrent development observations, not controlled
compiler regression claims. Generated tracked binaries were backed up and
returned to their original repository bytes; source and original untracked work
were preserved. The old cache build remains stopped.
