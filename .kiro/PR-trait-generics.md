# Static trait-constrained generics (SPEC §8.6)

## Summary

Implements static (monomorphized) trait-constrained generics end to end — type
checking **and** native code generation. A generic constrained by a trait now
compiles and runs: the trait method resolves on the bound type parameter, trait
**defaults** are inherited onto structurally-conforming concrete types (both the
`x.m()` and `m(x)` call forms), and a non-conforming type passed to a constrained
generic is rejected at the call site with a helpful diagnostic.

Before this change the feature was parse/AST-only: a trait method called on a
bound type parameter returned `Int` (a silent fallback) instead of the trait's
declared result type, so a valid program was rejected by the type checker and —
had it slipped through — dangled at codegen.

**Scope:** static monomorphized generics only. `dyn` runtime dispatch is out of
scope (separate, backend-heavy, tracked independently).

## Motivating example

```briev
trait Counter {
    defn bump(this: Self, amount: Int) -> Self;
    // default: written once in the trait, inherited by every conforming type
    defn bump_twice(this: Self, amount: Int) -> Self {
        term bump(bump(this, amount), amount);
    };
};

obj Tally {
    total: Int;
    defn bump(this: Tally, amount: Int) -> Tally {
        term Tally { total: this.total + amount };
    };
};

// one reusable helper, works for any T that conforms to Counter
defn bump_twice_generic<T: Counter>(this: T, amount: Int) -> T {
    term bump(bump(this, amount), amount);
};

node entry [beginprogram][true] {
    let t: Tally = Tally { total: 0 };
    let t2: Tally = bump_twice_generic(t, 5);  // 0 -> 5 -> 10
    endprogram Print#(t2.total);               // prints 10
};
```

All of the following now type-check **and** build to a native binary that
produces the correct result:

- `bump_twice_generic(t, 5)` — the `<T: Counter>` generic, resolving `bump` on `T`.
- `t.bump_twice(5)` — the trait default, method form, on a conforming `Tally`.
- `bump_twice(t, 5)` — the trait default, free form.

A non-conformer (e.g. a `Widget` with no `bump`) is rejected:

```
'bump_twice' requires T: Counter, but 'Widget' does not provide bump.
Add bump to 'Widget', or pass a type that conforms to Counter.
```

## How it works

### Front end (type checker) — `src/typechecker/mod.rs`

- **Carry the bound into scope.** Type-param *names* were tracked, but not their
  bounds. Added `fn_type_param_bounds` (per-defn registry) and a transient
  `active_type_param_bounds` (set while a generic body is checked), so inside the
  body the checker knows `T: Counter`.
- **Resolve a trait method on a bound param.** `resolve_bound_param_call` — when a
  call's argument is a bound type param `T: C` and trait `C` declares the called
  function, validate the call and return the result with `Self -> T`. Modeled on
  the existing `dyn Trait` resolution branch.
- **Trait defaults on conforming types.** `type_conforms_to_trait` (structural:
  the type provides every *required* trait function; defaults are supplied by the
  trait) + `resolve_conforming_trait_call` (resolve a default on a concrete
  conforming receiver, `Self -> concrete`), wired into both the free-call and
  method-call paths. Trait default **bodies** are now type-checked (they never
  were) with `Self` treated as a bound param of the trait.
- **Call-site conformance check.** `check_type_param_bounds` verifies each bounded
  param's inferred concrete type conforms, else a what/why/fix error naming the
  generic, the bound, the type, the missing operation(s), and the fix.

### Back end (native codegen) — `src/backend/llvm/`

- **Monomorphization (option b).** A top-level generic defn was emitted once,
  type-erased (`T` -> `i64`), so the body's trait call dangled. Now a generic defn
  is **specialized per concrete instantiation** at the call site: infer the type
  args from the argument registers, emit a copy under a mangled symbol
  (`bump_twice$Tally`) with the concrete types substituted into its
  params/return/body, root it live, and drain a worklist after reactor emission.
  Reuses the existing object-monomorphization machinery (`substitute_type`).
- **Free-call UFCS.** Inside a specialized body `this` is the concrete type, so a
  bare `bump(this, amount)` resolves to the object's member via the existing
  inline-member path (the same resolution the `x.m()` method form uses).
- **Trait defaults as `Self`-generics.** Each body-carrying trait function is
  registered as a generic defn over `Self`, so the same monomorphization
  specializes it onto conforming concrete types (both call forms).

### Spec

SPEC §8.6 is **unchanged** — it already specified "Static trait-constrained
generics are monomorphized by default" and structural conformance. The
implementation now fulfils the existing spec (contract-first; no spec weakening).

## Tests

- **Type-checker behavioral tests** (`src/typechecker/mod.rs`,
  `trait_generics_tests`):
  - a bound generic resolves its trait method to `T` (not the `Int` fallback);
  - a trait default resolves on a conforming type in **both** method and free form;
  - a non-conforming type at a `T: C` call is rejected with the correct diagnostic.
- **End-to-end fixture** `tests/tier1/trait_generics_smoke.bv` (program surface,
  built + linked + run by `tier1_corpus_compiles_links_and_runs`) with a pinned
  golden-output test `trait_generics_golden_output` in `tests/daily_use_smoke.rs`
  (prints `30` — three tallies of `bump_twice(_, 5) = 10` across all three forms).

`cargo test --lib`: no regressions (the only failures are the pre-existing
GPU/toolchain-dependent suites and the known malformed `adapters.dbvl` conformance
fixture — all unrelated to this change).

## Commits

- `feat(typecheck): resolve trait methods on bound type params (S1+S2)`
- `feat(typecheck): trait default methods on conforming types (S3)`
- `feat(typecheck): reject non-conforming types at trait-bound call sites (S4)`
- merge of `main` (brings the `llvm.memcpy` declaration fix this feature needed)
- `feat(backend): monomorphize trait-bounded generic defns (S6, WIP)`
- `feat(backend): monomorphize trait defaults onto conforming types (S6 complete)`
- `test(trait-generics): behavioral tests, E2E fixture, docs (S7)`

Full staged implementation log: `docs/plans/2026-10-12-static-trait-generics.md`.

## Known limitations / follow-ups (documented, non-blocking)

- **`dyn` runtime dispatch** remains deferred — this PR is static generics only.
- **`impl`-block conformance:** `type_conforms_to_trait` reads an object's own
  members only, not functions attached via `impl` blocks. No test exercises an
  `impl`-conforming type at a bounded generic yet; noted as a follow-up in
  `BUGS.md`.
- **Advanced trait features** (trait inheritance, associated types, multiple
  bounds per param, contract-refinement conformance) are not implemented — add
  only when a concrete need appears.

## Reviewer notes

- The change is **additive** in the hot paths: new resolution branches run only
  *before* the existing fallbacks, so a non-trait program is unaffected.
- The generic defn is no longer emitted type-erased; it is emitted once per
  concrete instantiation. An uninstantiated generic emits nothing (correct — dead
  code).
- `BUGS.md` carries a FIXED entry documenting the pre-fix gap and the fix.
