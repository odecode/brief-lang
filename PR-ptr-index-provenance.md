# fix: raw `Ptr<T>` scalar index load/store miscompiled via `inttoptr` provenance loss

## Summary

A raw `Ptr<T>` scalar element access — `base[i]` (load) and `base[i] = v` (store),
where `base` is an address held as an `Int` and recovered with `base as Ptr<T>` —
could read a **stale value**: under `-O3 -flto` the compiler hoisted/CSE'd a load
across a store to the *same* buffer. The fix emits these raw scalar loads and
stores as `volatile`, which LLVM cannot eliminate or reorder relative to each
other, closing the miscompile for every program.

This is a correctness fix on its own branch from `main`, with a regression test
and a `BUGS.md` entry, per the operating contract (fix codegen, never work around
it in stdlib).

## Where it was found

Building the recommender-app Task 8 serving oracle
(`examples/recommender/reference.bv`, `recommend_user`). A `picked[]` exclusion
array — a raw `Malloc#`-backed `Ptr<Int>` — was correctly marked `[1,1,1,1]`
(verified by a print *inside the writing defn*), yet a sibling defn
(`rec_argbest`) read `picked[3]` as `0` and re-selected the same item every pass,
returning already-rated items and running to `topn` instead of stopping.

## Symptom → discriminator → root cause (the evidence standard)

**Symptom.** `rec_argbest(picked=[1,1,1,1])` returned index `3` in one call chain
but `-1` (correct) in another over the *identical* array — same function, same
memory, different result across recursion frames.

**Discriminator (controlled A/B).** Hand-editing the emitted `.ll` to mark the
single `picked[i]` load `volatile` fixed the output exactly: `best=3` at `done=0`
became `best=-1` at `done=1`, and `rec_u3` went from length 5 to the correct
length 1. Nothing else changed.

Minimal probes under `scratch/ptr_store_crossdefn.bv` — lane A (cross-defn inline
store/read), lane B (helper-wrapped store/read), lane C (recursive selector with
an inline store + a callee reading the array, threading an accumulator, with first
Int and then Float scoring) — **all passed**. That is the key negative result: the
trigger is not generic cross-defn stores, not float recursion, and not the
accumulator shape. It needs the load and the store to live in **separate defns
large enough not to inline** (`rec_argbest` calls the heavy `cf_predict_ref`), so
the loads/stores survive into LTO where the alias analysis mis-handles them.

**Root cause (file:line).** The raw `Ptr<T>` scalar index LOAD
(`src/backend/llvm/emit_expr.rs`, `Expr::Index` → `raw_ptr_scalar` branch) and
STORE (`src/backend/llvm/emit_stmt.rs`, `Statement::Assign` → `Expr::Index` →
`scalar_pointee` branch) each recover the pointer with a **fresh**
`inttoptr i64 %base to ptr`. `inttoptr` produces a pointer with **no provenance**;
after inlining the load defn and store defn together, LLVM's BasicAA cannot prove
the two independent `inttoptr`-derived pointers alias, concludes the load does not
alias the store, and hoists/CSEs the load above the store → stale read.

This is one level deeper than the known `#8`/`#13` memory-attribute doctrine
(`BUGS.md`, "string concat miscompiles at -O2"), which governs a defn's *caller*
effect summary and correctly kept two `Malloc#`-wrapping *calls* distinct. The
attribute summary does not address load-vs-store provenance on raw `inttoptr`
pointers *inside/across* bodies. With `memory(argmem: readwrite)` (`#13`)
correctly set, the miscompile still occurs — confirming the two are independent
problems.

## The fix

Emit the raw `Ptr<T>` **scalar** element load and store as `volatile`:

- `src/backend/llvm/emit_expr.rs` — the `raw_ptr_scalar` load is now
  `load volatile <elem>, ptr %gep` unconditionally (previously volatile only
  under the `vol let` / MMIO `volatile_read` gate).
- `src/backend/llvm/emit_stmt.rs` — the `scalar_pointee` store is now
  `store volatile <elem> ...` unconditionally. Scoped to scalar pointees
  (`i8/i16/i32/i64/float/double`); the boxed-handle (List/dyn/String i64-carrier)
  else-branch keeps its prior `vol_obj` gate, untouched.

Two volatile accesses cannot be reordered relative to each other, so a
`base[j] = v` store can no longer be moved around a `base[i]` read. This is sound
for **every** raw-buffer access regardless of inlining — it does not depend on
recognizing the specific shape that triggered it.

**Why not just the load?** Volatile only orders against *other* volatiles. A
volatile load with a non-volatile store would still let LLVM move the store. Both
halves must be volatile.

## Options considered and NOT chosen

1. **Per-function recovered-pointer cache** (reuse one `inttoptr` per base
   register so load and store share an SSA `ptr`, which AA relates). **Rejected:**
   the load and store in this bug are in *different functions*
   (`rec_argbest` vs `rec_select`); a per-function cache cannot make two
   functions share an SSA value, so it would not fix the cross-function case —
   exactly the one that bites. It also risks reusing a pointer across a base
   redefinition unless carefully scoped.

2. **TBAA / `!alias.scope` / `!noalias` metadata** (incl. the existing
   declared-but-unused `StateAliasScope` `!99`). **Rejected:** type-based
   aliasing metadata makes AA *more aggressive* (more disambiguation), which is
   the wrong direction — it cannot force a load to *observe* a prior store. The
   lever needed is provenance/ordering, not type disambiguation.

3. **Thread one canonical provenance-carrying `ptr` from the single `as Ptr<T>`
   cast** through every index/deref/field access (instead of re-`inttoptr`-ing
   per access), so AA relates all accesses to the same underlying object.
   **Not chosen now (deferred):** this is the *correct long-term* fix and
   preserves optimization, but it is a deep change touching the cast, index
   (load/store), deref-assign, and field paths — higher risk, larger surface.
   It is the documented future-work successor (see below).

Chosen: **volatile scalar raw-`Ptr<T>` loads/stores** — minimal, local,
guaranteed correct for all programs, correctness-first per the operating contract.

## Optimization impact (important — this project prioritizes performance)

`volatile` on raw `Ptr<T>` **scalar** buffers disables, for those accesses:

- **SLP / load-store vectorization** — volatile element loads/stores are not
  vectorized, so tight `Vector`/`Matrix`/`IntVec` element loops over raw buffers
  lose auto-vectorization on the element accesses.
- **Redundant-load elimination / GVN** — a repeated `base[i]` in the same scope is
  re-loaded each time rather than reused.
- **Store-to-load forwarding** — a `base[i] = v` immediately followed by reading
  `base[i]` will reload instead of forwarding `v`.

Scope of the cost: **only raw scalar `Ptr<T>` element accesses** (the
`base[idx]` / `base[idx] = v` form on `Malloc#`-backed buffers). It does **not**
touch: `%State` field accesses (TBAA'd, unchanged), boxed-handle collection
buffers (List/dyn/String carrier path, unchanged), aggregate/row-view stores, or
any non-`Ptr<T>` path. The matrix/CSR hot loops in `matrix.bv` /
`rating_population.bv` use exactly this scalar form, so they are affected — the
tradeoff is deliberate and accepted for correctness.

### How to preserve/restore the optimization in future work

Replace volatile with **provenance preservation** (rejected option 3):

1. Make `as Ptr<T>` emit the *one* `inttoptr` and bind the resulting `ptr` as a
   first-class pointer value.
2. Thread that single `ptr` through the index load/store, deref-assign, and field
   paths (a `Ptr<T>` SSA value in `TypedRegister`, not an `i64` re-recovered per
   access), so every access GEPs off the *same* base pointer. BasicAA then relates
   them by shared provenance and keeps store→load ordering **without** volatile.
3. Once accesses carry provenance, drop the volatile (revert the two writes here;
   the `BUGS.md`/code "Undo" notes point at the exact lines) and re-enable
   vectorization on raw buffers.
4. Gate the change with a pre/post benchmark A/B on the matrix/CSR corpora
   (per Golden Rule 12 / the Performance Recovery Protocol) and keep this bug's
   regression test — but assert provenance (same `ptr` base) instead of volatile.

A complementary avenue is emitting `!noalias`/restrict-style metadata derived
from the *proof* that two buffers are distinct (the compiler already proves
single-writer/independence facts) — but that restores disambiguation between
*different* buffers, not the store→load ordering on the *same* buffer, so it is
additive to (not a replacement for) provenance threading.

## Tests / verification

- `cargo test --lib` — new regression test
  `raw_ptr_scalar_index_load_and_store_are_volatile`
  (`src/backend/llvm/emit_toplevel.rs`) asserts the emitted IR for a scalar
  `Ptr<Int>` index load/store carries `load volatile` / `store volatile`.
- End-to-end: the recommender serving oracle (`recommend_user`) returns the
  correct `[i3]` for u3 and empty for u0 after the fix, matching the
  volatile-`.ll` A/B result, with no source-level workaround.

## Merge-order dependency

Independent compiler fix; no dependency on other fix branches. The recommender-app
stdlib/app work (Task 8) depends on THIS fix to pass its serving gate — verify the
oracle gate on an integration branch after this lands, then pick it up on `main`.
