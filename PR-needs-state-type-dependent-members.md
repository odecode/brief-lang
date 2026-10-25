# fix(analysis): type-dependent needs_state for monomorphized trait members

## Summary

A trait default (or trait-constrained generic) monomorphized onto a concrete
type whose members are **stateful** was emitted **stateless**, so its body's call
to a genuinely state-taking helper referenced an undefined `%state` and clang
rejected the IR. The verdict was computed type-agnostically; this fix makes it
depend on the concrete type the default is specialized onto.

## Symptom

Building a generic writer over a growing byte buffer failed at codegen:

```
.ll: error: use of undefined value '%state'
  %t15 = call i64 @grow_to_fit(ptr %state, i64 %arg0, i64 %t3)
```

`grow_to_fit` genuinely needs state (it calls `Malloc#`), so it is correctly
emitted taking `ptr %state`. But its caller — the monomorphized `put_cstr$GrowBuf`
(and `write_tagged$GrowBuf`) — was emitted **without** a `%state` parameter, so
the `%state` it tries to pass does not exist.

## Why this is type-dependent

The same trait default is stateless on one implementer and stateful on another:

- `put_cstr$ByteBuf` — `ByteBuf.put_u8`/`put_bytes` only do `Store#`/`Copy#`.
  Genuinely **stateless**.
- `put_cstr$GrowBuf` — `GrowBuf.put_u8`/`put_bytes` call a free-standing
  `grow_to_fit` which calls `Malloc#`. Genuinely **stateful**.

A single type-agnostic verdict for `put_cstr` cannot be correct for both.

## Root cause (two compounding gaps)

In `src/analysis/export_abi.rs` and `src/backend/llvm/emit_expr.rs`:

1. **Obj members were never indexed into the needs-state fixpoint.**
   `index_program` had arms for top-level `Definition`, `Export`, trait defaults,
   etc., but **no arm for `TopLevel::TypeDef` / `TopLevel::Impl`**. So obj members
   were not nodes in the call graph. When a trait default called a required method
   by bare name (`put_cstr` calls `put_bytes`), the lookup `regular.contains_key("put_bytes")`
   was false, the call was treated as external/frgn → stateless, and the
   `member → member → Malloc#` path was invisible.

2. **The monomorphization site copied the base verdict verbatim.** At the
   specialization site, the mangled copy's `needs_state` was set to
   `defn_needs_state.get(base_name)` — the single type-agnostic verdict, with no
   per-instantiation recomputation. Even with members indexed, one bare-name
   verdict cannot differ per concrete `Self`.

## Fix

- **`export_abi.rs`:** index obj/impl member defns under **type-qualified keys**
  (`type_member_key` → `GrowBuf::put_bytes`), so `ByteBuf::put_bytes` (stateless)
  and `GrowBuf::put_bytes` (stateful via `grow_to_fit` → `Malloc#`) are **distinct
  fixpoint nodes** — a bare-name key would collide them. A new
  `type_stateful_members(items)` derives, from the same least-fixpoint, the set of
  concrete types that have at least one state-taking member.

- **Backend:** thread `type_stateful_members` onto the codegen context (populated
  beside `compute_defn_needs_state`). At the specialization site the mangled
  copy's verdict becomes:

  ```
  needs_state = base_needs || (any concrete binding ∈ type_stateful_members)
  ```

  So `put_cstr$GrowBuf` / `write_tagged$GrowBuf` take `%state`, while
  `put_cstr$ByteBuf` stays stateless.

### Why this is sound and not a patch

- **Soundness:** a specialization onto a type with a stateful member carries
  `%state`; its callers are made stateful transitively by the same rule, so the
  parameter is always supplied.
- **Bounded over-approximation:** a specialization that happens not to call the
  stateful member still gets a `%state` param. That is valid IR (a threaded,
  unused leading pointer) and matches the pass's documented conservative-keeping
  stance. The alternative — walking each specialized body to resolve exactly which
  members it calls — was rejected as more fragile for no observable benefit.

## Tests

Two behavioral regression tests in `export_abi::tests` (they parse real Briev
source and assert the analysis the backend consumes):

- `obj_member_reaching_stateful_intrinsic_is_indexed_stateful` — a member reaching
  `Malloc#` through a free-standing helper is a type-qualified node judged
  state-taking; a sibling `Store#`-only member stays stateless.
- `type_stateful_members_reports_only_types_with_a_stateful_member` — the set the
  monomorphization site consults reports the stateful type and not the stateless
  one.

`cargo test --lib` is green.

## Verification

- Self-contained probe: a generic `write_pair<S: Sink>` used with a `Growing`
  type whose member reaches `Malloc#` builds and runs (prints `9`) where it
  previously failed the `%state` IR check.
- The full combined case (two implementers with a same-named member, one stateful)
  builds and runs (prints `7` then `9`) — this additionally relies on the
  independent liveness member-collision fix (see that PR) so the free-standing
  helper is not judged dead. The two fixes are independent and compose.

## Notes for the merge

Branched from `main` (`fix/needs-state-type-dependent-members`), independent of
feature work. The end-to-end case that surfaced it is a growing byte buffer
(`GrowBuf`) on a separate feature branch; once this and the liveness fix are on
`main`, that branch picks them up.

Files changed:

- `src/analysis/export_abi.rs` — member indexing under type-qualified keys,
  `type_member_key`, `type_stateful_members`, and the two regression tests.
- `src/backend/llvm/context.rs` — the `type_stateful_members` context field.
- `src/backend/llvm/mod.rs` — populate it beside `compute_defn_needs_state`.
- `src/backend/llvm/emit_expr.rs` — OR the per-type verdict into the mangled
  copy's `needs_state`; the `concrete_type_name` helper.
- `BUGS.md` — the diagnosis and fix entry (`FIXED 2026-10-15`).
