Evaluate a field receiver exactly once. `make_object().field` previously invoked `make_object()` twice; a resource-producing factory could leak the first resource and expose the second one.

The discriminator is a counter incremented by the factory: direct, nested and assignment-RHS field reads must increment it once. Tuple projection remains covered too.

`src/backend/llvm/emit_expr.rs` first evaluated the receiver to select tuple/object lowering, then `emit_field_access` evaluated it again. Pass the existing typed register into the general field loader, retaining the existing dereference path through a shared helper. Dispatch-only HIR callers explicitly request evaluation by passing None. This applies to every receiver expression, independently of factory or type names.

Native tests execute at O0 and O3. Integration socket tests also verify no descriptors remain open. Final validation is recorded below for this branch. This branch is based on main and has no prerequisite fix.

Validation on 3fb01c97: 3,499 library tests passed (source-conformance sweep delegated to CI), native regression passed at O0 and O3, and cargo build passed without warnings. Praetor comparison found no new diagnostics. The HTTP integration additionally checks descriptor closure with Valgrind; its final merged verification is recorded below.

Source locations: src/backend/llvm/emit_expr.rs:1633 and :3425–3435 (3fb01c97), the dispatcher-to-field-loader handoff and reused receiver register.

Final combined verification (integration fd52b03f): 3,511 library tests and all 10 integration tests pass, including the new O0/O3 regressions, enum/list retention, descriptor availability, integer-output allocations, nonblocking transport and wasm32 tuple verification. The full ten-program IR determinism gate passes. Build has no warnings; Praetor has no new diagnostics. Clang 17 and 18 execute all three corpus programs with identical semantic output after excluding only the explicitly labelled timing values; the raw-byte matrix reports a parity failure on those elapsed times and is not claimed as passing. Source conformance remains delegated to CI; Kani cannot start on the executor's older glibc.

The pinned integration also passes all controlled HTTP cases, two 50-request Valgrind cases (zero errors/lost bytes/open network descriptors), and a 25/25 successful GET /movies smoke at 5/s against an existing native server executable. This verifies the client path, not a fresh server build or server capacity.

CI integration correction: merged upstream main 78be8eb6 and fixed its new HIR Field caller, which still passed the old register-name argument. The receiver is not emitted on that path, so it passes None; the AST dispatcher retains Some for its already evaluated receiver. Follow-up 22ce21eb audits all three callers and runs the counter fixture with HIR emission unset and enabled, at O0 and O3. On the updated base: 3,499 library tests, the native gate, ten-program determinism, eight-program AST/HIR byte equality, build/check and Praetor comparison pass. Clang 17/18 semantic parity also passes with the previously documented labelled-timing comparator limitation.

Full replacement CI passed on 22ce21eb: https://github.com/Randozart/briev-lang/actions/runs/42030028017. The unfixed transport compiler also confirms the native counter fixture is a negative discriminator: it exits 1 at the first assertion; the corrected compiler succeeds in all four emission-mode/optimization combinations.
