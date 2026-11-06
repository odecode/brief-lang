Calls through trait default bodies were missing from ownership analysis, so locally allocated inputs could not be reclaimed even when the concrete method only borrowed them. A default such as `twice(value: Self) { read(value) + read(value) }` must inherit the effects of the receiver's concrete `read`, including a capturing implementation.


```briev
trait Access {
    defn read(value: Self) -> Int;
    defn twice(value: Self) -> Int { term read(value) + read(value); };
};
obj Local {
    ptr: Ptr;
    defn read(value: Local) -> Int { term Load#(value.ptr,8); };
};
defn closed() -> Int {
    let value: Local = Local { ptr: Malloc#(8) };
    Store#(value.ptr,7,8);
    term value.twice();
};
```

This should license a closed allocation region. Replacing `read` with a body
that passes `value.ptr` to an unclassified external call must remain a barrier.

Register default bodies as Self-specialized generic callables after ordinary definitions, matching the backend's default registration. Preserve top-level precedence and concrete member overrides. Resolve free-call concrete members and generic return shapes so chained calls retain their receiver type. Required body-less methods remain concrete requirements.

Root cause: `analysis/reclamation/walk.rs` omitted trait registration and free-call member resolution, and method expression typing did not follow generic return types. `walk/traits.rs` centralizes default registration and output substitution. Regression pairs use a local read versus a capturing concrete method, through both chained and free calls; another pair checks concrete and top-level shadowing.

Verification: 3,513 library tests pass (source-conformance sweep delegated to CI), warning-free cargo build, and no new Praetor diagnostics. The combined authenticated client passes five admission/save/prediction operations and independent durable receipt checks, with zero Valgrind errors and zero lost bytes. Kani cannot start on this WSL glibc; no model-checking claim is made.

Based on upstream 9f49b2f8. Independent of the entropy and tuple-field fixes; neighboring walker edits may need an ordinary merge. Bug record, ownership architecture and plan are included.
