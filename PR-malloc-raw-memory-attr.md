# fix(backend): Malloc#-wrapping defn must be memory(readwrite), not memory(read)

## Summary

A user `defn` whose only raw-memory operation is `Malloc#` was emitted with the LLVM attribute `memory(read)`. Under `-O3 -flto`, LLVM then common-subexpression-eliminated two identical-argument calls into a SINGLE allocation - so two allocations that must be distinct returned the same pointer, aliasing and causing a later double-free. The fix marks such defns `memory(readwrite)` so LLVM cannot merge the calls.

## The bug

Discovered building lib/std/rating_population.bv (recommender-app Task 5): a dual-CSR builder allocates two IntVecs of the same length; they aliased, and freeing both aborted with `free(): double free detected` (SIGABRT).

### Controlled A/B (discriminator)

- Two DIRECT `Malloc#(16)` calls returned DISTINCT addresses.
- Two `ivec_new(n)` calls (a defn whose body is `Malloc#(n*8) as Int`) returned the SAME address.

So the defect is not Malloc# itself - it is that the user-defn WRAPPER was treated as side-effect-free and became CSE-eligible.

### IR evidence

`@ivec_new` was defined with attribute group #8 = `memory(read)`, and the two identical calls `call i64 @ivec_new(ptr %state, i64 %t26)` were merged. A read-only function with identical arguments is a textbook CSE candidate for LLVM.

## Root cause

`definition_touches_raw_memory` (src/backend/llvm/emit_toplevel.rs) decides a defns function-level memory attribute: a body touching raw memory gets memory(readwrite) (#13), otherwise memory(read) (#8). Its RAW intrinsic list was:

    Load# Store# Alloc# Free# Copy# Fill# VolatileLoad# VolatileStore# SysCall#

It included Alloc# but NOT Malloc#. So a defn whose only raw-memory op is Malloc# was judged side-effect-free and got memory(read).

## The fix

Add Malloc# to the RAW list. Malloc# is the allocating sibling of Alloc# and is observable in the intrinsic registry (src/intrinsic_signatures.rs); a function that allocates has an observable effect and must not be memory(read). This is a correctness completion of the list, not a workaround - the omission was the bug.

```rust
const RAW: &[&str] = &[
    "Malloc#", "Load#", "Store#", "Alloc#", "Free#", "Copy#", "Fill#",
    "VolatileLoad#", "VolatileStore#", "SysCall#",
];
```

## Tests

- New regression test `defn_wrapping_malloc_is_not_memory_read` (src/backend/llvm/emit_toplevel.rs): generates IR for a defn `alloc_box(n) = Malloc#(n*8) as Int` called twice and asserts the definition line uses the readwrite attribute group (#13), never the read-only one (#8). Passes.
- End-to-end: with the rebuilt compiler, the two `ivec_new(n)` calls return distinct pointers and the double-free is gone.

## Note on the test environment

The repo has a standing set of ~37-38 environment-dependent test failures (GPU/SPIR-V/PTX device tests and cross-assembler `bad` hardening tests) that require toolchains/hardware absent in this build environment. This change touches only the CPU LLVM defn-attribute selector and does not affect those backends.

## Files changed

- src/backend/llvm/emit_toplevel.rs - add Malloc# to the RAW list; +1 regression test.
- BUGS.md - entry documenting the bug and fix.
