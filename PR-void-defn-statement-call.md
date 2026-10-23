# Fix: `-> Void` user defn called as a statement emitted invalid IR

## Symptom

A user `defn ... -> Void` called as a bare statement produced invalid LLVM IR
that clang rejected:

```
scratch/sock_loopback.ll:3718:3: error: instructions returning void cannot have a name
 3718 |   %t20 = call void @sockaddr_free(ptr %state, i64 %t0)
```

Found building the L2 socket module (recommender-app Task 1): `sockaddr_free`,
`sock_close`, and bytes.bv's `buf_free`/`grow_free` are all `-> Void`.

## Minimal repro (`scratch/void_call_probe.bv`)

```briev
defn free_it(addr: Int) -> Void { Free#(addr as Ptr); term; };
let n: Int = 1;
node report [n > 0][n > 0] {
    let addr: Int = Malloc#(8) as Int;
    free_it(addr);          // → %t = call void @free_it(...)
    term;
};
```

## Root cause (file:line)

`src/backend/llvm/emit_toplevel.rs`, `callee_declares_void`. The backend's
void-call guard (which emits an UNNAMED `call void @f(...)`) keyed only on an
EMPTY registered return list:

```rust
if let Some(types) = self.ctx.defn_return_types.get(name) {
    return types.is_empty();   // only implicit-void txns
}
```

A defn declared `-> Void` registers a return list of `[Type::Void]` (non-empty),
so the guard returned false and `finish_user_call` fell through to the
named-result path (`%v = call void @...`) — a result name on a void call, which
LLVM forbids. Only implicit-void txns (empty list) were handled.

## Fix (why it is sound, not a patch)

`callee_declares_void` now also treats an explicit `[Type::Void]` first return
type as void:

```rust
return types.is_empty()
    || types.first().map(|t| matches!(t, Type::Void)).unwrap_or(false);
```

Both void forms now take the UNNAMED `call void @f(...)` path (with a fresh
dummy register for the expression value). Additive; the non-void path is
unchanged. The frgn path already had the equivalent guard
(`sig.result_type.is_void()`); this brings user defns in line.

## Tests

`backend::llvm::tests::test_void_defn_statement_call_is_unnamed` — asserts the
IR contains `call void @free_it` but NOT `= call void @free_it`. Green.

## Verification

`brievc build scratch/sock_loopback.bv` now compiles and links; running it
prints the loopback round-trip (`sent=1`, `recv_count=1 byte=65`,
`roundtrip_ok=true`).

## Merge order

Independent — no dependency on the method-call fix.
