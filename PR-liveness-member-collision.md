# fix(analysis): walk all same-named obj member bodies in defn-liveness

## Summary

Defn-liveness could judge a live free-standing helper as dead when two objects
provided a member of the **same name**. The emitted (inlined) member body still
called the helper, so the post-emission IR-scan soundness net aborted the build
with `defn liveness: emitted code calls unreached defn(s) [...]`. This fix keeps
every same-named member body in the liveness closure so no object's member call
edges are lost.

## Symptom

Building a program with two objects that each provide a same-named member — a
normal consequence of a trait requirement (e.g. `put_u8` provided by both
`ByteBuf` and `GrowBuf`) — panicked at codegen:

```
thread 'main' panicked at src/backend/llvm/mod.rs:5574:
defn liveness: emitted code calls unreached defn(s) ["grow_to_fit"] — add the
intrinsic→helper row in src/analysis/defn_liveness.rs (intrinsic_helpers) or
root the caller; see docs/architecture/defn-liveness.md
```

The helper (`grow_to_fit`) was reachable only from the second object's member
body. The IR-scan net did its job: it caught a real emitted-but-unlive call
rather than letting it become a silent linker failure.

## Root cause

`src/analysis/defn_liveness.rs` indexes obj/typedef **member** bodies by their
bare name:

- `index_defn` / `index_txn` insert member bodies into `defns` / `txns` keyed by
  bare name (`or_insert` / `insert` — first- or last-wins).
- Obj members legitimately **share a name across objects** (that is exactly what
  a trait requirement is: `ByteBuf.put_u8` and `GrowBuf.put_u8` both exist).
- So `defns["put_u8"]` retained only **one** body.

When live code constructs the *other* object and roots its `put_u8`, the worklist
pops the name and walks whatever single body is stored under it — the wrong
object's body. If the stored body happens not to call the helper (e.g.
`ByteBuf.put_u8` calls nothing, while `GrowBuf.put_u8` calls `grow_to_fit`), the
helper's call edge is never followed and the helper is judged dead.

Members are inlined at their call sites at emission (they are not emitted as
standalone symbols), so the emitted `GrowBuf.put_u8` body *does* call
`grow_to_fit`. Liveness said dead; emission said called — the IR scan fired.

### Controlled A/B that isolates it

- **One** object whose member calls a free-standing helper → builds and runs
  (prints `7`). Single-member path has always worked.
- Add a **second** object with a **same-named** member declared *first*, whose
  body does **not** call the helper → the build panics `unreached defn [helper]`.

Only introducing the same-name collision changes the outcome, which pins the
cause to the bare-name index, not to the member-walking path in general.

## Fix

Add a collision-safe multimap that keeps **every** member body (and its
contract) under its bare name, and walk all of them when the name goes live:

```rust
/// Obj members share a name across objs by design (a trait requirement like
/// `put_u8` on both `ByteBuf` and `GrowBuf`). `defns`/`txns` keep only ONE
/// same-named body; keep ALL of them here and walk every one when the name
/// goes live, so no member's call edges are lost.
member_bodies: HashMap<String, Vec<(&'a [Statement], &'a Contract)>>,
```

- Populated by a small `index_member_body` helper, called from `index_typedef`
  and the `TopLevel::Obj` arm alongside the existing `index_defn` / `index_txn`.
- The worklist closure, when a name enters the live set, walks the usual
  `defns` / `txns` / `contracts` entry **and** every member body + contract
  registered under that name.

### Why this is sound and not a patch

- **Soundness:** every member body under a live name contributes its call edges,
  so a helper reachable from any object's member is kept.
- **Over-approximation is bounded and intentional:** walking a member body for an
  object that was not constructed can only keep a few extra helpers live. The
  pass already documents this coarse-sound stance ("over-approximation is
  deliberate and harmless").
- **No behavior change elsewhere:** top-level `defns`/`txns` keep their existing
  first/last-wins semantics; the usage-triggered construction-rooting path is
  untouched. The change is purely additive to the closure walk.

## Tests

Two behavioral regression tests in `defn_liveness::tests` (they parse real Briev
source and assert the liveness verdict — testing the contract, not the
implementation):

- `same_named_member_bodies_all_contribute_call_edges` — the bug: two objects
  with a same-named `bump` member (the first calls nothing, the second calls a
  free-standing `helper`); asserts `helper` is live.
- `single_member_body_edge_is_followed` — the control: one object, confirming the
  single-member path still works.

`cargo test --lib` is green.

## Verification

- The minimal collision reproduction, which previously panicked at build, now
  builds and runs (prints `7`).
- `cargo check` and `cargo test --lib` pass.

## Notes for the merge

This fix is independent of any feature work and is branched from `main`
(`fix/liveness-member-name-collision`). The end-to-end case that first surfaced
it (a growing byte buffer `GrowBuf` whose `put_u8` reallocates via `grow_to_fit`)
lives on a separate feature branch; once this merges to `main`, that branch picks
it up and the full growing-buffer program builds and runs.

Files changed:

- `src/analysis/defn_liveness.rs` — the `member_bodies` multimap, the
  `index_member_body` helper, the worklist walk, and the two regression tests.
- `BUGS.md` — the diagnosis and fix entry (`FIXED 2026-10-15`).
