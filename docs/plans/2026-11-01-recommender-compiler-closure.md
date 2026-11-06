# Recommender compiler closure — 2026-11-01

Goal: compile and exercise the external recommender app, retaining the bounded
visible-page selection change. No benchmarks requested. Library tests run last;
the human runs cargo commands per the recommender workflow.

## First increment: nested object enum capacity

Controlled repro: scratch/enum_nested_object_payload.rbv fails with Receipt
32 bytes versus a 16-byte enum payload. The app fails identically for RatingSaved.
EnumLayoutPlanner counts object fields as words, whereas struct_type_size consumes
the resolved universe byte size, including nested objects. Planning must consume
the same size before applying inline thresholds and choosing enum representation.
Unknown resolved sizes must not license inline storage. Preserve the existing
AST-only planner for callers without a universe.

Validation: planner regression cases for nested objects, threshold crossing,
unknown size and boundary enums; build the minimal browser repro, then the app;
run the existing browser peer gate with selection assertions. Repeat for further
compiler failures. Run library tests only after browser work is complete.

Documentation: update enum layout rationale, LLVM memory architecture, BUGS.md,
the net-stack bug log and recommender tasks. Preserve existing rationale comments.
No commits until the human reviews the logical unit (workflow requirement).

## Second increment: callable transaction prologue

The human rebuilt successfully. With an explicit compiler config directory the
nested enum panic is gone. App LLVM verification now rejects module-level alloca
before select_movie. scratch/callable_txn_local_slot.rbv reproduces with a local
assigned in a guard. Move the existing prologue after entry, still before param
binding. Add a regression forbidding stack allocation outside function bodies.
The compiler outside its source tree requires explicit --config-dir config;
without it the app reports a Float/Int mismatch. Keep invocation explicit.

## Third increment: enum field context

The frontend builds and selection smoke passes. Native server diagnostics expose
OwnedOperationJob inheriting Result<ProfileUpdate,AdmissionError> rather than its
field type OperationJob. This is independent of resolved object capacity. Scope
constructor context to declared field type and restore it afterward; keep enum
typing through field ownership. External app Vector/Matrix references are also
migrated to stdlib FloatVector/FloatMatrix; launcher config is now explicit.

## Fourth increment: inline object projection ownership

Both targets build after field scoping. Native startup reaches listen then
SIGSEGV in free(0x90), called from worker_channel_close. GDB shows a nested buffer
handle inside a dead stack frame. Inline object pattern bindings are interior
views into enum result slots; unwrap can return those views and fields retain
them. Materialize an owned byte image for bound object values. Borrowing requires
a proved non-retaining projection consumer, which is not currently recorded.

Projection lifetime gate: tests/tier1/enum_object_projection_lifetime.bv compiles
and runs with the fixed compiler. Linking the original/fixed emitted IR at O0
produces failure/success respectively; the original optimized binary happened
to pass, so O0 is essential to expose the dead-frame read. No timing recorded.

## Fifth increment: nested object ABI stability

Live app registration/login/select/accept work. Save-confirmation decoding
corrupts the stack. Object inline eligibility wrongly depends on enum nesting
depth, so a Result<Event,...> reserves boxed-object child capacity while Event
constructors/matches use standalone inline-object capacity. Finite object images
do not participate in enum recursion; remove the enum-depth cap from their
eligibility. Regression compares embedded child capacity with standalone layout.

## App acceptance

Both targets compile with ~/briev-target/debug/brievc, explicit compiler config
and lib root. Browser selection smoke passes (no selection requests; unchanged
page and ratings). Native server stays running and serves the full catalogue.
Real browser against briev_recommender_test passes registration, login, movie
selection, four-star save, and server saved confirmation. Full pending-peer gate
passes optimistic paint, ordering, duplicates, fallback, failure, cancellation
and stale-session handling. Praetor has zero new diagnostics against HEAD.
Only after these checks: cargo test --lib started as final verification.

## Final regression results

Corrected planner fixtures to register resolved type metadata; parse_and_check
alone deliberately returns an unregistered universe. The callable-slot assertion
now excludes comments. No production code changed during these fixture fixes.
Final focused results: enum-layout 12/12; LLVM crash-regressions 8/8; browser
pending-peer passes. App save smoke passes with the final compiler binary.

The full library run reports failures outside the focused app gates, including
SPIR-V 1.6 output validated against a 1.5 test target and the wasm tuple-return
IR expectation. Full conformance sweep remains running at this recording point.
No claim of a fully green library suite. No benchmarks were run.

## Selection deployment correction

The human launches `bash examples/recommender/run-demo.sh --rebuild-app` from
the compiler checkout. That source copy still contained the old selection
handler; its generated IR called browser_profile_overlay and catalogue refresh.
The prior app fix had been applied only in the external checkout. Apply the same
visible-page selection handler here, update this checkout's browser regression,
and rebuild target/recommender-web. Focused browser profiling checks all 12
visible choices; each applies synchronously with no transport request. Observed
handler average about 8 ms, maximum about 12 ms, in the isolated browser fixture.
This is click-path diagnosis, not a benchmark-suite result.

The earlier full library run finished: 3412 passed, 19 failed. Four initial new
fixture failures were corrected and rerun (enum layout 12/12, crash regressions
8/8). The broader failures include SPIR-V target-version and ABI expectations;
no claim of a green full suite. This app-only source correction does not change
compiler Rust and does not require another full library run.
