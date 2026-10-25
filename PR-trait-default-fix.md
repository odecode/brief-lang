# fix(backend): derive needs_state for monomorphized trait defaults

## Summary

A monomorphized **trait default method** was emitted with a hidden `ptr %state`
parameter, while its (correctly stateless) caller passed no state - producing
invalid IR that `clang`/`opt` rejected:

```
error: use of undefined value %state
  %t0 = call i64 @put_two$FixedSink(ptr %state, i64 %arg0, i64 %arg1)
```

Static trait-constrained generics otherwise worked (both typecheck and runtime).
This bug was specific to the **trait-default** codegen path and blocked any trait
whose default methods are built on its required methods.

## The bug

When a generic is constrained by a trait (`defn write_pair<S: Sink>(...)`) and
calls a trait **default** method, the backend monomorphizes that default per
conforming type (`put_two` becomes `put_two$FixedSink`). Each emitted function
is either *stateless* or *state-taking* (the latter gets a hidden `ptr %state`
first parameter that threads the reactor program state). That decision comes from
the `needs_state` analysis in `src/analysis/export_abi.rs`.

The analysis walks `TopLevel` items and indexes every `Definition` into a
needs-state call graph. **Trait default functions were never indexed**, because
they live inside a `TopLevel::Trait`, not as a top-level `TopLevel::Definition`.
So when the backend looked up the monomorphized copy verdict by the original
(unmangled) name, the lookup missed and fell back to:

```rust
let needs_state = self.ctx.defn_needs_state.get(mangled).copied().unwrap_or(true);
```

The `unwrap_or(true)` means the default was treated as **state-taking**. The
emitted `put_two$FixedSink(ptr %state, ...)` then demanded a `%state` its
stateless caller `write_pair$FixedSink(i64, i64)` never had.

### Why only defaults

A **required** (body-less) trait method is just the concrete type own `obj`
member, resolved through that type registration - it was never affected. Only
body-carrying **defaults** go through the monomorphization path that hit the
missing index. (Confirmed with a control probe: a generic that calls a required
method twice itself builds and runs fine.)

## The fix

Index trait default methods into the needs-state call graph, so the monomorphized
copy inherits the original default **derived** verdict through the same
least-fixpoint call-graph walk every other `defn` gets - rather than defaulting
to state-taking.

In `index_program` (`src/analysis/export_abi.rs`):

```rust
TopLevel::Trait(t) => {
    for func in &t.functions {
        // or_insert mirrors the backend "a real top-level defn wins" rule:
        // a concrete same-named defn is not shadowed by a trait default.
        if !func.body.is_empty() {        // defaults only (body-less = required)
            regular.entry(func.name.clone()).or_insert(func);
        }
    }
}
```

Key properties:

- **Derived, not blanket-flipped.** A pure default that only calls sibling
  members and constructs a struct is correctly stateless; a default that touches
  a state field or calls a `txn`/stateful intrinsic correctly **stays**
  state-taking. The verdict comes from the call-graph analysis, not a hardcoded
  default.
- **Required methods untouched.** Body-less trait functions are not indexed -
  they resolve as the concrete type own members.
- **Precedence preserved.** `or_insert` keeps the existing "a real top-level
  defn of this name wins over a same-named trait default" rule.

## Tests

Four regression tests added in `export_abi::tests`, including:

- `pure_trait_default_is_stateless` - the repro default (`put_two` calling
  `put_one` twice) derives `needs_state == false`.
- `stateful_trait_default_keeps_state` - a default that reaches program state
  stays state-taking (proves the fix derives rather than blanket-flips).

Verified gates (all green):

| Check | Result |
|-------|--------|
| Repro probe_sink_generic.bv (default via generic) | builds + runs, prints 2 |
| Baseline probe_trait_3.bv (generic trait method) | prints 10, no regression |
| Control probe_sink_nodefault.bv (required method) | prints 2, no regression |
| probe_sink_contracts.bv (per-impl contract variance) | typechecks OK |
| cargo test --lib | green |

## Repro (before this fix)

```
trait Sink {
    defn put_one(sink: Self, val: Int) -> Self;
    defn put_two(sink: Self, val: Int) -> Self {   // default built on the required op
        term put_one(put_one(sink, val), val);
    };
};

obj FixedSink {
    len: Int;
    cap: Int;
    defn put_one(sink: FixedSink, val: Int) -> FixedSink
        [sink.len < sink.cap][term.len == sink.len + 1]
    {
        term FixedSink { len: sink.len + 1, cap: sink.cap };
    };
};

defn write_pair<S: Sink>(sink: S, val: Int) -> S {
    term put_two(sink, val);
};

node entry [beginprogram][true] {
    let fixed: FixedSink = FixedSink { len: 0, cap: 8 };
    let after: FixedSink = write_pair(fixed, 42);
    endprogram Print#(after.len);   // expected: 2
};
```

Before: clang fails with use of undefined value %state.
After: builds and prints 2.

## Files changed

- `src/analysis/export_abi.rs` - index trait defaults into the needs-state call
  graph; +4 regression tests.
- `BUGS.md` - entry documenting the bug and fix.
