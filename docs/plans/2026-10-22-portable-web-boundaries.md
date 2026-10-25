# Portable web boundaries: compiler prerequisite handoff

This continues the task-14 plan of 2026-10-21 and records its compiler carve-out.
The integration checkout is the execution surface; the main-based fix branch
contains compiler/configuration changes and generic regression fixtures only.

The implementation adapts native registers at boxed-word, call-signature and
pointer-buffer boundaries, retains persistent initialized objects on the heap,
sizes view snapshots dynamically, and propagates helper writes for browser DOM
invalidation. Portable target configuration selects the browser prelude.
Foreach and enum-pattern elaboration retain lexical type information so declared
collection operators resolve normally. No recommender vocabulary is recognized.

Documentation changes: backend allocation/value/state contracts and the browser
host-boundary decision record. Existing rationale comments are retained. BUGS.md
records the concrete failures and regression gates. Stdlib and app changes have
separate branches; merge prerequisites before executing the app.

Verification on 2026-10-22: clean main-based compiler branch `cargo check --lib`
passes. Native cache/server regression runners and all three native server
property gates pass. Browser heap/transport, actual WASM JSON and 1100-element
Unicode collection snapshot gates pass. Chrome passes registration/login,
duplicate/distinct ratings, cold-start gating, latest live updates, reconnect,
logout and 375px layout. Quick LLVM determinism passes. Full determinism has
six byte-identical entries and the existing giantnode liveness rejection;
there is no observed byte drift. Installed clang-17 corpus: recommender OK,
multinode missing-input skip, giantnode existing compile rejection.

Praetor comparison covers exactly changed files. The new fixed-point analysis
and heap helpers add no diagnostic categories. The large existing member-body
function improves from four reported issues to three; existing oversized-method
warnings remain. The complete final library result and runtime harness ledger
are appended after the outstanding runs finish. The user's accepted 38
environment failures are compared by exact test name and are not repaired.

## Final verification (2026-10-22)

The final full library run completed: 3178 passed, 38 failed, 743.48 seconds.
The failure-name set exactly matches the accepted task-13 baseline: no added
or removed failures. Both new lexical-scope regressions pass. Final release
build completed without new warnings, and its backend/browser artifacts built
successfully. The release frontend boots at localhost:8081 without page errors;
native backend OPTIONS and frontend HTML return HTTP 200. Compiler, stdlib,
cache and required frontend gates are complete; optional task 14.4 is skipped.
