# Recommender float buffer API alignment

## Goal

Make the recommender example compile against the current `std/matrix.bv`
contracts after `main` renamed its heap-backed float handles to `FloatVector`
and `FloatMatrix`.

## Baseline and evidence

Running `examples/recommender/run-demo.sh` in WSL with PostgreSQL online built
the release compiler, then failed compiling the backend. The diagnostics
reported `Vector`/`FloatVector` and `Matrix`/`FloatMatrix` mismatches. In
`lib/std/matrix.bv`, `vec_new`, `vec_get`, `vec_set`, and `vec_free` use
`FloatVector`; `mat_new`, `mat_get`, `mat_set`, and `mat_free` use
`FloatMatrix`. The recommender's six affected source files still declared the
old names. `IntVec` remains the integer-only API and will not change.

## Change

Update recommender float-buffer fields, parameters, return types, local
annotations, and struct constructors to use `FloatVector` and `FloatMatrix`.
Keep `Vector` where it denotes compiler/language collection types or appears in
unrelated code. Preserve allocation, indexing, and ownership behavior.

## Documentation and verification

Keep comments that explain the distinction between integer and float buffers,
updating only stale type names. Record the verified cause and outcome in
`BUGS.md`. Re-run the demo script with PostgreSQL online; it is the acceptance
gate for backend compilation, frontend compilation, and runtime startup. Run
`cargo test --lib`, `cargo build`, and Praetor on changed source directories
before committing, as required by the repository checklist.

## Results

Pending verification.

2026-10-28: backend and frontend compile against the renamed float handles.
The live demo serves the catalogue and app. Authentication required the separate
pooled-object assignment repair recorded in 2026-10-28-recommender-auth-state.md.
The launcher now exposes LLVM 17 to both builds and enforces LF line endings.
