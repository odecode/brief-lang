An enum's native Bool payload and a boxed Bool parameter can reach a binary operation as i8 and i64. LLVM rejects the resulting mixed-width comparison. For example:

```briev
enum Toggle { Value(Bool) };
defn agrees(value: Toggle, expected: Bool) -> Bool {
    match value { Value(flag) => flag == expected, }
};
```

Normalize unequal scalar integer representations before the existing binary dispatcher. Extend the narrower value using its declared protocol's signedness and preserve the wider physical type. Equal-width, floating and vector paths retain their existing behavior. No type-name or algorithm matching is introduced.

The defect is at the binary-emission boundary in `src/backend/llvm/emit_expr.rs`; `integer_operands.rs` centralizes normalization for all four callers, including the HIR path and literal patterns. The fixture exercises both Bool orders, equality/inequality, signed and unsigned narrow values and ordering. Native execution covers AST/HIR at O0/O3.

Verification: 3,511 library tests pass (source-conformance sweep delegated to CI); cargo build has no warnings; native AST/HIR regression passes at O0/O3; no new Praetor diagnostics. The combined integration additionally passes ten-program IR determinism and eight-program AST/HIR byte parity. Clang 17/18 run all three matrix programs with identical semantic output; the raw comparator flags only labelled timing values. Kani cannot start on this executor because glibc 2.32–2.34 are unavailable.

Based on upstream 9f49b2f8; independent of the ownership-effect PRs. Architecture contract, bug record and plan are included.
