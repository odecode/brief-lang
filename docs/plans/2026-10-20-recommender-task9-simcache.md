# Plan: Recommender-app Task 9 — Similarity_Cache + refresh

**Date:** 2026-10-20
**Spec:** `.kiro/specs/recommender-app/` (tasks.md Task 9; design "The Similarity
Cache + Refresh"; requirements §6, §10.4)
**Branch discipline (WORKFLOW.md):** build/run on `integration/ptr-provenance`
(carries the `fix/ptr-index-provenance` compiler fix that Task 8's serving needs
and that Task 9's cache reads inherit — the SimCache matrices are raw `Ptr<T>`
blocks). **Commit the Task-9 deliverables on the vessel `feat/fullstack-webapp-demo`**
(tip `ec38e15f`, Task 8). The vessel does not yet carry the fix; that is expected
— the fix lands on `main` via its own PR and the vessel picks it up through main.
Until then, the vessel's Task-9 code is verified on the integration branch.

## Who runs what (WORKFLOW 2026-10-20)

The **human** runs every `brievc`/`cargo` command from their WSL shell. I author
the `.bv` on the Windows tree, say the exact command, and interpret the pasted
output. Standing commands (from WORKFLOW "Build and test strategy"):

```
# build the compiler we run (only needed if Rust changes — none expected here):
cd /mnt/c/Users/wotto/code/briev-lang && source ~/.cargo/env \
  && CARGO_TARGET_DIR=~/briev-target cargo build --release
# fast typecheck of the app file:
~/briev-target/release/brievc check examples/recommender/cf_engine.bv
# build + run the harness (runtime gate):
~/briev-target/release/brievc run examples/recommender/cf_engine.bv
```

## What Task 9 is

The CF engine (`cf_engine.bv`) currently recomputes the means + both PCC matrices
**per prediction** (O(population) per request). Task 9 adds the **served snapshot**:
precompute both PCC matrices and both mean vectors once into a `SimCache`, so each
prediction is O(k) reads (Req 6.3 / 10.4). Plus the refresh machinery: compute a
fresh cache off to the side and swap the served pointer atomically (Req 6.4/6.5),
a `PopSignature` (record count + source mtime) that decides freshness (Req 6.6),
and binary persistence to `simlist.txt.bin` (Req 6.1/6.2).

Correctness oracle is unchanged: every cached value is checked against
`reference.bv`'s `pcc_imputed_users` / `pcc_imputed_items` on the 4×4 fixture,
within 1e-6. The cache is a **memoization** of the engine's existing sim', so the
gate is "cached value == on-the-fly `sim_user`/`sim_item` value" (which the
engine already anchors to the oracle).

## Increments (teaching cadence — one, stop, explain, gate)

Required (non-`*`) sub-tasks only. The `*` property/unit tests (9.3, 9.5, 9.6,
9.7) are skipped per the legend unless the human asks.

- **9.1 `obj SimCache` + `simcache_build`.** Precompute `user_sim` (nusers²),
  `item_sim` (nitems²) `Matrix`es and `user_mean`/`item_mean` `Vector`s from a
  `(pop, Means)`, plus `nusers`/`nitems`. Lower-triangle-once + mirror (symmetry).
  Gate: `simcache_user_sim(sc,a,b) == sim_user(pop,m,a,b)` for all 4×4 pairs,
  diagonal 1.0, symmetric; item side likewise. O(k) accessors.
  **✅ MET 2026-10-20** (integration/ptr-provenance debug binary) — all 7 gate
  lines true; Task 6/7/8 unchanged-green. Cache = memoization, no new claim.

- **9.2 Off-to-the-side compute + atomic pointer swap.** A served-snapshot holder
  (`obj Served { cache_ptr: Int }`) and `served_swap(old, new)`: build the new
  SimCache in fresh `Malloc#` blocks, assign the holder's pointer in ONE step,
  free the old snapshot after the swap. Teach WHY the single-process poll model
  makes this atomic by construction (no preemptive reader can see a half-built
  snapshot). Gate: reads before the swap see the old values, reads after see the
  new; a "refresh" that changed a rating changes exactly the affected pair.
  **✅ MET 2026-10-20** — all 6 `swap_*` lines true. Model: `Served { slots: IntVec }`
  control block (objs are immutable handles, so indirection lives in the block, not
  a field). NOTE: field name `cell` is reserved → renamed `slots`.

- **9.4 `PopSignature` + binary persistence.** `obj PopSignature { nnz; mtime }`;
  `sig_fresh(a,b)` = (nnz==nnz && mtime==mtime). Persist the SimCache to
  `simlist.txt.bin` with a header `[magic][nusers][nitems][nnz][mtime]` then the
  raw matrix+vector blocks (`Copy#` into a String-shaped buffer → `write_file`);
  load = `read_file` → verify magic+signature → `Copy#` blocks back. A signature
  mismatch ⇒ stale ⇒ recompute+rewrite. A short/corrupt read ⇒ treated as absent
  (recompute), never a bad cache. Gate: build→write→load round-trips to identical
  matrices; a bumped signature forces recompute; a truncated file is rejected.
  **✅ MET 2026-10-20** — all 16 `sig_*`/`sc_sig_*`/`persist_*` lines true. Flat
  image = 5-word header + 4 raw blocks (`Copy#`, bit-exact). Three correct
  compiler rejections along the way (not bugs): `[true][true]` trivial contract,
  prelude-visibility-vs-emission (needed explicit `import "std/os/fs.bv"`),
  `write_file: Result<Int,Int>`.

## Status: Task 9 COMPLETE (2026-10-20)

All three required sub-tasks (9.1/9.2/9.4) green on the integration branch;
`*` tests (9.3/9.5/9.6/9.7) deferred per the legend. Deliverables committed on
the vessel `feat/fullstack-webapp-demo`. No compiler bug surfaced.

## Risk ledger (design "Compiler / Language Risk Ledger")

- **⚠ reactor pointer-swap refresh** (the Task-9 named risk): the swap is a plain
  field assignment between poll iterations. Exercised here with an explicit
  old/new holder; any miscompile of the pointer store is a compiler bug → repro
  under `scratch/`, fix on `fix/<name>` from main, BUGS.md — never worked around.
- **Large `Malloc#` Float matrices** (inherited from Task 4): the nusers²/nitems²
  blocks at 943/1682 scale are the risk-ledger large-allocation path. The 4×4
  fixture gate is correctness; a scale allocate/round-trip is noted for Task 10/12
  wiring (first-green wants f64 — confirm `Float` resolves to f64 at scale, the
  Task-6 note).
- **Raw `Ptr<T>` scalar load/store** now volatile (the merged fix) — correct, at
  a vectorization cost documented in `PR-ptr-index-provenance.md`. The cache's
  matrix reads ride that path; correct by the fix.

## Documentation maintenance (Golden Rule 13)

- `tasks.md`: tick 9.1/9.2/9.4 with a one-line learned-note each; record the live
  branch set in START HERE if it changes.
- This plan: record the gate results as they pass.
- `BUGS.md`: any compiler bug surfaced (OPEN→FIXED + root cause), per the
  cross-cutting rule.
- No architecture-doc contract changes expected (app-layer code over existing
  stdlib primitives); if a stdlib primitive gains a function, update its header.

## Out of scope for Task 9 (later tasks)

- Reading the REAL u.data/DB mtime + record count (Task 10 parser + schema wires
  the live signature source; here the signature is a recorded `(nnz, mtime)` the
  mechanism compares).
- The periodic timer that triggers refresh between poll sweeps and the admin
  refresh endpoint (Task 12 server reactor) — Task 9 provides the swap primitive
  they call.
- `simlist.txt` fixture comparison as a committed test (9.7 is `*`).
