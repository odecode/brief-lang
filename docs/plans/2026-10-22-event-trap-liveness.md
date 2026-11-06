# Event trap liveness follows emitted reads

2026-10-22. Main-based compiler prerequisite on `codex/event-trap-liveness`.

## Evidence and hypothesis

I02's real WASM contract fixture includes collection arrow assignments through
the JSON codecs. The generated WASM IR includes `event_strict_trap`, its
`write_all` helper, and Linux `briev_syscall`, even though the fixture has no
event read. The earlier closed-reflection correction removed unrelated
`Prefetch` assembly, isolating this remaining route.

`src/analysis/defn_liveness.rs::walk_stmt` seeds the full task/event helper set
for every `ArrowAssign`, because an event-wire write lowers to the event-fire
helper. Collection writes use the same AST form. This broad seed emits task
scheduling code and target-specific trap/output paths for ordinary collection
updates. The backend's emitted-call fixpoint already derives backend-generated
event-fire calls, so the statement-level seed is unnecessary.

## Implementation and verification

Remove the broad task/event seed from `ArrowAssign` and add a liveness regression
proving a collection arrow does not keep unused event helpers. Then build the
real I02 WASM fixture and inspect the emitted IR. Existing event-write/read
programs must still compile through the emitted-call soundness fixpoint.

Run the library suite against the accepted baseline, build without new
warnings, and run directory-scoped Praetor. Update `defn-liveness.md` and
`BUGS.md` with the call-closure contract and evidence. This is a general
reachability correction; it does not identify the recommender or collections.
