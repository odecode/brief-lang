# fix(backend): Float tuple-destructure elements unboxed, not bound as i64

## Summary

Destructuring a Float-family tuple returned from a defn
(`let (a, b): (Float, Float) = pair();`) bound each name to the raw `i64`
loaded from the tuple's heap slot. The tuple stores each Float **boxed** as its
i64 bit pattern, so any later float use of `a` or `b` got an i64-defined
register, and clang rejected the module. The destructure now unboxes each
Float element back to its native `float`/`double`. This is the exact inverse
of the store side.

## Symptom

A program that destructures a Float tuple and uses an element as a float
failed at the clang step:

```
error: '%tN' defined with type 'i64' but expected 'float'
```

Minimal reproduction:

```briev
defn two() -> (Float, Float) {
    term (1.5, 2.5);
};
defn useit(a: Float, b: Float) -> Float {
    term a + b;
};
let tick: Int = 0;
node run [tick < 1][tick == 1] {
    let (x, y): (Float, Float) = two();
    println!("x={} y={}", x, y);
    println!("sum={}", useit(x, y));
    tick = 1;
    endprogram;
};
```

This surfaced while building the recommender reference oracle
(`examples/recommender/reference.bv`, on the feature branch), which returns
Float pairs and triples from helper defns.

## Root cause

The two sides of the tuple ABI disagree about Float elements:

- **Store side (correct):** `emit_tuple_materialize`
  (`src/backend/llvm/emit_expr.rs:2613`) passes every element through
  `adapt_to_i64` (`src/backend/llvm/helpers.rs:2325`) before `store i64`. A
  32-bit Float is boxed as `bitcast float -> i32; zext -> i64`, and a 64-bit
  Float as `bitcast double -> i64`.
- **Load side (the bug):** the destructure arm of `Statement::Let`
  (`src/backend/llvm/emit_stmt.rs`, `if names.len() > 1`) emitted
  `load i64` for each slot and bound the name to that register unchanged,
  while recording the element's declared Float type in `let_binding_types`.

So the binding's *type* said Float but its *register* was an i64. Every later
float use (`fadd`, a `float` call argument, `print_float`) got an i64 operand.

### Discriminator

The destructured registers before the fix (illustrative; register numbers
vary):

```llvm
%t16 = load i64, ptr %t15          ; bound directly as `a`
%t20 = load i64, ptr %t19          ; bound directly as `b`
%t24 = fadd fast float %t16, %t20  ; i64 registers in a float position -> invalid
```

After the fix:

```llvm
%t16 = load i64, ptr %t15
%t17 = trunc i64 %t16 to i32
%t18 = bitcast i32 %t17 to float   ; bound as `a`
...
%t24 = fadd fast float %t18, %t22
```

Only the element's Float type changes the outcome. `Int` tuples were never
affected, because their boxed i64 is already their native register.

## Fix

A small helper, `unbox_tuple_float_element` (`src/backend/llvm/emit_stmt.rs`),
is called on each loaded element before binding:

- If the element type is a member of the **Float protocol**, the helper reads
  the type's LLVM width from the casting graph (`llvm_type`):
  - `double`: `bitcast i64 -> double`
  - `float`: `trunc i64 -> i32; bitcast i32 -> float`
- It records the native register in `reg_float_cache`, so later reads of the
  binding resolve the float value. It then binds the name to that register.
- Non-Float elements, or a width the graph doesn't resolve as
  `double`/`float`, return the loaded i64 unchanged (same as before).

### Why this is sound and not a patch

- **Exact inverse of the store.** Each arm undoes exactly what `adapt_to_i64`
  does for that width, so storing and then loading a value gives back the
  original bits.
- **Protocol-driven, not name-matched.** Dispatch is Float protocol
  membership plus the resolved LLVM width, never a comparison against a
  specific type name. Every Float-family type (`Float`, `Float32`, `Float64`,
  `Double`, user aliases) takes the correct arm. A name-matched version
  (`elem_ty == Type::float64()`) would silently miss `Double` and any alias.
- **Mirrors existing machinery.** This is the same unboxing the boxed Float
  param-slot read already does in `emit_expr.rs` (`is_protocol_member(&ty,
  "Float")` + `llvm_type == "double"`).
- **Additive.** The non-Float path is unchanged. The destructure arm's logic
  moved into a named helper, so `emit_statement` gains no complexity (Praetor
  metrics are identical before and after).

## Tests

There are two behavioral regression tests in `src/backend/llvm/tests.rs`. Both
compile real Briev source with a registered type universe, the same way the
real pipeline does. Without the universe, the store side can't see Float
membership and never boxes the element, so the bug isn't exercised.

- `test_float_tuple_destructure_unboxes_f32_elements`: `(Float, Float)`.
  Asserts the `trunc i64 ... to float` unbox and a `fadd fast float`.
- `test_float_tuple_destructure_unboxes_f64_elements`: `(Float64, Float64)`.
  Asserts the `bitcast i64 ... to double` unbox and a `fadd fast double`.

Both also run `assert_no_i64_in_float_positions`, the existing IR
mini-verifier that rejects any i64-defined register used in a float
operation. This is the exact failure the fix removes.

## Verification

- `cargo test --lib float_tuple_destructure`: both new tests pass.
- `cargo test --lib`: full suite green.
- `cargo build`: no new warnings.
- The end-to-end repro above builds with the patched `brievc` and runs,
  printing `sum=4`.
- Praetor (`praetor validate --warn`) on the changed files: the same 14
  diagnostics as on `main`, all in existing code (`emit_statement`'s size,
  6-parameter helpers, long test builders). Nothing new from this change.

## Known adjacent gap (not in this PR)

`adapt_to_i64` also boxes **Bool** (`zext i8`), **Char** (`zext i32`) and
**String/Blob** (`ptrtoint`) tuple elements, and the destructure still binds
those as the raw `i64`. A `(String, Int)` destructure is likely the same class
of bug. It's left out to keep this PR to the Float case that was reproduced
and verified. The same helper is the natural place to extend it.

## Notes for the merge

The branch is `fix/float-tuple-destructure`: one commit on `main`, independent
of any feature work and with no merge-order dependency. The recommender
reference oracle on the feature branch is blocked on this fix and picks it up
once this merges to `main`.

Files changed:

- `src/backend/llvm/emit_stmt.rs`: the `unbox_tuple_float_element` helper and
  its call in the tuple-destructure arm.
- `src/backend/llvm/tests.rs`: the shared IR builder and the two regression
  tests.
- `BUGS.md`: the diagnosis and fix entry (`FIXED 2026-10-19`).
