# Preserve match values when another arm terminates

A value-producing match with a trapping arm passed checking but emitted an
undefined return register. For example, returning 42 from one Bool arm and
trapping in the other failed LLVM compilation.

The match type probe now excludes arms that cannot reach the merge and resets
and restores its termination state. Existing pattern-binding, block, and alloca
snapshots are preserved. Continuing Void arms and all-terminating matches retain
their existing behavior.

Validation:
- Four regression tests cover both arm orders, pointer results, nested
  termination, and continuing Void control; emitted IR verifies with clang.
- Cargo check/build pass without new warnings. Native value and trap paths pass.
- Full library suite: 3157 passed, 38 failed; all failure names occur in the
  earlier baseline report, including data-adapter schema conformance.
- Praetor: no new diagnostics. Focused IR is deterministic; six broad corpus
  modules are identical between processes. Giantnode cannot emit IR because of
  an unchanged frontend liveness rejection.
- Installed clang 17 passes the recommender toolchain check. Multinode lacks the
  root input fixture; giantnode has the same frontend rejection. The broad
  determinism and toolchain harnesses are not claimed fully green.

This branch is based on main and contains only the compiler fix, regressions,
and documentation. Application and stdlib changes are excluded.