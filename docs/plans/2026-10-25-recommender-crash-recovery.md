# Recommender startup and interaction crash recovery

Scope: reproduce and repair startup and usage failures in the current checkout,
preserving the pre-existing uncommitted application and compiler work.

Evidence: Node's syntax check rejects generated app.mjs at the first star
button: `this._txn("select_stars")(, 1)`. The browser reports the same syntax
error and never initializes. The trigger generator prepends a comma to an
argument list that no longer includes an implicit state argument.

Steps: repair general trigger generation; add behavioral browser regression
coverage for startup, catalogue, selection, rating, and repeated updates; build
and exercise the native service with the real catalogue and dedicated test DB;
investigate subsequent failures with captured errors. Run cargo test --lib,
cargo build, Praetor on changed directories and applicable compiler gates.

Documentation: preserve existing rationale comments, add dated rationale for
changed event semantics, update frontend architecture and BUGS.md with verified
causes and test outcomes. This is a correctness repair, not a performance plan.

Results will be appended as each gate completes.

## Investigation record

The native empty-worker model allocated one CSR offset per side, although a
zero-row CSR still reads the terminal offset. Allocating and initializing both
offset entries removed the AddressSanitizer overflow. An independent optimized
JSON probe then identified an escaping sret stack image: the ordinary LTO link
crashed, disabling inlining passed, and replacing the escaping temporary with
owned storage in the actual IR passed all parse categories. Removing alias
attributes did not fix it and was rejected.

Browser startup additionally exposed missing heap imports, a malformed trigger
argument list, and target-width mismatches in reflection and stateless calls.
Actual generated WASM now parses integers and decimal recommendation scores.
The collection snapshot gate passed Unicode, empty globals, 1100 entries and
reset after persistent global headers and dynamically sized snapshot storage.

The worker's next ASan failure was a guarded negative index: eager `&&` called
the previous-item predicate at index zero. The existing logical CFG lowering
was connected to ordinary expressions, including mutable parameter/local slots
and dominance-safe caches. Its three behavioral regression tests passed.

The browser catalogue scan exhausted the WASM stack. Experiment: run LLVM 17
`opt -S -passes=mem2reg,tailcallelim` on the actual generated app IR, then the
same llc/wasm-ld commands and original export list. The original module trapped
in `browser_catalogue_scan`; the transformed module completed catalogue load,
rating submission and saved/recommendation events. This is a bounded-stack
correctness gate; no throughput claim or timing result is made.

The remaining catalogue corruption was traced to generic callable transactions:
the concrete `iter_chain<MovieCard>` called an erased adapter with incompatible
element strides. Extend the existing specialization worklist to transactions,
preserving their contracts and convergence semantics. The snapshot fixture now
also concatenates twelve distinct struct elements to cover this boundary.

## Verified recovery results

The compiler-level regressions cover declared call widths, boolean literal
widths, helper transaction boundaries and pooled object replacement across
reactor firings. All four pass. The real browser/server test passes against the
generated WASM app and native PostgreSQL service: registration, login, initial
ratings, recommendations while a save is database-blocked, and saved
confirmation all work. The recommendation list is not rendered again after
save; there are no follow-up GETs or synchronous XHR, and the browser reports
no long task while the database is blocked.

The same test found that one catalogue request grew the server RSS by roughly
412 MiB while producing an 85,469-byte response. Writing through one owned
GrowBuf now returns a byte-for-byte identical response and measured a 0 KiB
RSS change for a repeat request. The browser peer suite, actual WASM collection
snapshot/JSON probes, LLVM logical regression group, view compiler tests and
GLUE web-generator tests pass. Worker process gates pass shutdown/reaping,
crash/restart, timeout, malformed-message isolation, and the prediction pool
gates pass fairness and generation cleanup.

The broad `cargo test --lib` run reproduces the known host-dependent GPU and
SPIR-V failures and also trips existing environment-sensitive tests; those are
outside the recommender recovery and were not changed. The application-specific
gates above pass. Praetor reports the repository's existing diagnostics and no
new diagnostic for the new regression tests or object bridge. Windows reports
line-ending normalization notices for changed cross-platform files; `git diff
--check` passes.
