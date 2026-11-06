Statement matches must preserve every continuing arm. A function matching an enum payload, conditionally returning from its first arm and unconditionally returning from its final arm incorrectly lost the code following the match. Reordering the arms changed the result.

For example, `match value { Number(n) => { when n < 0 { term 10; }; }, _ => { term 20; } } term 42;` must return 42 for `Number(1)`.

In `src/backend/llvm/emit_stmt.rs`, statement-match emission reused the final arm's `terminated` flag for the merge block. Keep that block open: continuing arms and the emitted unmatched edge reach it. LLVM can eliminate an actually unreachable merge. No pattern-specific treatment is added.

The native fixture checks guarded arms, reversed arm order, an empty fallback and entirely returning arms at O0 and O3. Library, build and integration validation are recorded below for this branch. This branch is based on main and has no prerequisite fix.

Validation on bb69d282: 3,499 library tests passed, with the source-conformance sweep delegated to CI; the native regression passed at O0 and O3; cargo build passed without warnings. Praetor found no new diagnostics against the changed-file baseline. Final combined IR determinism and toolchain checks are recorded with the HTTP integration.

Source location: src/backend/llvm/emit_stmt.rs:2947–2958 (bb69d282), the statement-match merge-block termination decision.

Final combined verification (integration fd52b03f): 3,511 library tests and all 10 integration tests pass, including the new O0/O3 regressions, enum/list retention, descriptor availability, integer-output allocations, nonblocking transport and wasm32 tuple verification. The full ten-program IR determinism gate passes. Build has no warnings; Praetor has no new diagnostics. Clang 17 and 18 execute all three corpus programs with identical semantic output after excluding only the explicitly labelled timing values; the raw-byte matrix reports a parity failure on those elapsed times and is not claimed as passing. Source conformance remains delegated to CI; Kani cannot start on the executor's older glibc.

The pinned integration also passes all controlled HTTP cases, two 50-request Valgrind cases (zero errors/lost bytes/open network descriptors), and a 25/25 successful GET /movies smoke at 5/s against an existing native server executable. This verifies the client path, not a fresh server build or server capacity.
