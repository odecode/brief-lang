## Preserve tuple value types across construction and reads

An unannotated object-tuple binding such as `let (left,right) = endpoints();`
previously reached LLVM field access with type Int and panicked. Annotating only
the destructure masks the returned-value case; constructing a local tuple still
loses its element types. Numeric projection also failed to decode float slots,
while destructuring did not restore String pointer slots consistently.

```briev
obj Endpoint { descriptor: Int; };
defn endpoints() -> (Endpoint,Endpoint) {
    term (Endpoint { descriptor: 17 }, Endpoint { descriptor: 25 });
};
let (left,right) = endpoints();
```

`emit_tuple_materialize` in `src/backend/llvm/emit_expr.rs` returned Int despite
building a heterogeneous product. It now retains Type::Tuple, including the
hoisted path, while preserving the existing target-width integer handle ABI.
Destructuring uses the initializer type when no annotation is present. Both
read paths use one fixed-i64-slot decoder; floats, String pointers, raw Ptr
integer handles and narrow/nested tuple handles preserve their representations.

The same type erasure in reclamation analysis made closed product scopes
unclassified and retained allocations. Product return types, local bindings
and numeric projection now preserve metadata there too. Returned pointer aliases
remain outside local reclamation regions.

Focused validation: runtime mixed-value fixture at O0/O3, native Valgrind with
zero errors/loss, and nested tuples compiled, LLVM-verified and executed as
wasm32. Empty and hoisted products and retained aliases have library regressions.
Full-library and integration results are recorded in the accompanying plan.

Based on upstream 84f37578; no other PR is required. A separate nonblocking
transport feature uses the fix but contributes no files to this PR.

Final gates: 3,501 library tests passed; both integration tests passed; cargo build finished without warnings. Combined integration: 10/10 IR determinism programs; Clang 17/18 output parity on the available recommender input (two dataset-dependent rows skipped because u.data is absent).
