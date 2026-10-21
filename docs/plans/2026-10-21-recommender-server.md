# Task 12: complete backend server

User requested the entire task 12 after the 12.1 teaching checkpoint. Continue
in verified increments without stopping between them. No performance optimization
or benchmark claim; task 16 retains throughput/latency/concurrency measurement.

1. Load consistent baseline+account populations, explicitly map IDs to engine
   rows, and consume cached similarities for predictions. Recompute active-user
   weights on rating changes; full refresh builds then swaps a complete model.
2. Parse/validate JSON and route every API endpoint with token-scoped identity.
3. Add bounded nonblocking input/output, saved partial-write progress, EOF/error
   cleanup and HTTP-to-WebSocket transitions including buffered trailing bytes.
4. Handle masked WebSocket text/continuations/control frames and owner-only pushes.
5. Wire startup/schema/bootstrap, periodic refresh and reactor scheduling. Verify
   native loopback register/login/rate-five/live/isolation plus malformed and
   fragmented traffic, refresh, EOF and backpressure. Run compiler/library gates.

Update architecture applications/recommender-server.md and the task ledger with
wire shapes, limits, ownership, snapshot and authentication contracts. Preserve
existing rationale comments. Compiler bugs get minimal repros, independent fixes
and regression guards per WORKFLOW; do not work around them in application code.
Commit approval remains required by WORKFLOW.

## Native results

All task-12 substeps, including the requested optional tests, are implemented.
run_server.sh passes reactor slots, JSON grammar/Unicode/numeric boundaries,
PostgreSQL API routing, forced-backpressure output (524292 exact bytes), invalid
HTTP framing, half-close, failed-refresh preservation, complete register/login/
five-fragmented-ratings/live-owner flow, HTTP-triggered push, refresh row mapping,
WebSocket protocol errors and cleanup. Three proptest properties each pass 128
native cases. The active cached predictor is additionally compared with the
existing full CF engine after refresh at nonconstant ratings, with a finite-value
gate before tolerance comparison.

Standalone server builds; invalid PORT exits with a concrete configuration
diagnostic. Perpetual service intent is declared with a residence law. New raw
connection state uses 128 bytes per slot and owns its fragment buffer too.

Two compiler fixes surfaced: ordinary collection rebinding and Float Abs overload
names. Both are prepared on separate main-based worktrees/branches, with minimal
native regressions and focused unit tests. JSON grammar/progress fixes and
selective dependency imports are stdlib corrections, not app workarounds.
The user explicitly excluded interpreter work: no interpreter source/test edits
remain. Performance targets are still task 16; no timing claim is made.

Compiler build passes without warnings. After collection rebinding, the full
library suite reports 3167 passed and exactly the same 38 failure names as the
captured 3164/38 baseline. Float Abs adds two focused passing tests; the full
post-Abs suite is running. IR determinism quick gate passes all three corpus
programs across separate processes. Installed-toolchain matrix: clang-17
recommender OK; multinode skips because u.data is absent; giantnode is rejected
by the existing reactive-liveness check before codegen. Those skipped/failed
rows are not claimed green.

Praetor passes changed application/fixture/db/net directories. The new compiler
helper has no diagnostics. Controlled HEAD/current comparison of existing large
backend files retains the same diagnostic identities; emit_statement's existing
cyclomatic/cognitive metrics increase by one for the additive dispatch guard
(278->279 / 818->819). No pre-existing diagnostics are hidden or called green.
JSON/std directories pass. Final backend directory checks retain existing
diagnostics and add none for the intrinsic helper/tests.

## Final verification

Final full library suite: **3169 passed, 38 failed**, with exactly the same 38
failure names as the captured 3164/38 baseline (sorted name diff is empty).
All five added compiler tests pass. Compiler builds without warnings. Native
Float32/Float64 Abs plus integer control pass; finite-gated cached/full-engine
agreement and all server gates pass. The complete runner's three native proptest
properties each pass 128 cases. Final IR determinism quick gate again passes all
three programs. Standalone server configuration errors flush before exit.

Additional final gates cover negative fd/slot lookup, failed-listener reporting,
legal optional HTTP header whitespace and trimmed WebSocket nonce hashing.
Unusable poll/listener state exits with a concrete diagnostic instead of spinning.

## Stop checkpoint — requested by user

Task 12 is complete, including 12.4/12.5/12.8 properties and 12.9 integration.
Final additional protocol/loopback gates pass after header-whitespace handling;
cached_engine_agrees=true and all ownership/lifecycle checks are true. Final
library result is 3169 passed / the same 38 baseline failure names. Native
properties, build, application/fixture/stdlib Praetor and IR determinism pass;
existing backend Praetor diagnostics and toolchain skips are described above.

Current working branch: integration/ptr-provenance. Changes are uncommitted per
WORKFLOW's approval rule. Separate main-based fix worktrees are prepared at
.worktrees/task12-rebind (fix/collection-assignment-rebind) and
.worktrees/task12-abs (fix/float-abs-intrinsic); both contain uncommitted intended
fixes. PR body drafts are at the repository root. Existing user untracked work
was preserved. No interpreter changes remain. Resume with review/commit approval
and branch carve-outs; the next implementation checkpoint is task 13, not more
task-12 coding. Do not rerun completed checks unless source changes warrant it.

No commits/pushes: the workflow requires explicit review/approval first. PR body
drafts and clean compiler-fix worktrees are prepared without disturbing existing
untracked work. Application changes remain on integration/ptr-provenance.
