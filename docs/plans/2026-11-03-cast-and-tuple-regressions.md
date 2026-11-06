# Cast and tuple regression closure — 2026-11-03

Restore the raw Bit-category encoding edge without changing Data's representation-preserving String cast. Verify explicit-width Bits inputs and existing String/Data round trips. The obsolete bare Bit fixture resolves through Data and must not be used as evidence for the raw Bit category.

The wasm tuple test predates reconciliation with upstream commit f5bb16e6e, which deliberately made tuple handles target-width. Preserve that ABI; replace the i64-only assertion with checks for consistent construction, return, call and destructuring on both 32- and 64-bit targets, then run the existing wasm tuple fixture.

Preserve existing working-tree changes. Update casting and ABI rationale comments, BUGS.md and the fullstack task ledger. Build and run focused reproductions first; run library tests only at final verification. Known SPIR-V environment failures are accepted. Commit/push only after the workflow's human review step.

Verification: native String/Bits/String and String/Data/String printed hello;
the browser cast/tuple fixture and standalone recommender fixture passed. The
final library run reported 3422 passes and 11 SPIR-V failures, with only the
conformance sweep pending. The user explicitly requested cancelling that sweep
and creating PRs; origin CI owns its final result.

Upstream reconciliation: current origin/main already contains the encoding
route and does not contain the obsolete tuple test from this integration tree.
Carve out only the concrete bit-cast width/pointer fixes and guarded tail-return
fix into independent branches from origin/main. Preserve all local integration
work. The user's PR request authorizes the commits and pushes for these branches.
