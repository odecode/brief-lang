# Load transport investigation

Date: 2026-11-05
Status: open compiler prerequisites; no capacity measurement.

Local main and fork/main were fast-forwarded to origin/main 3737396b.
The integration working tree and its prior changes are preserved.

The existing recommender functional suite passed with the November 4 debug
binary and LLVM 18 on PATH. A new controlled stream-peer probe exposes a
compiler panic: unannotated destructuring of returned (Socket,Socket) binds
both elements as Int. emit_stmt.rs discards the initializer tuple type.
A candidate consuming that type got past this panic, but a library regression
covering a locally constructed tuple still failed: emit_tuple_materialize
returns Int too. The incomplete candidate and its library test were removed.
A complete fix must preserve semantic tuple types across construction, returns,
local bindings and destructuring without changing the target handle ABI. The
probe remains in the app's benchmarks/load/probes/transport_progress.bv.

The rebuilt compiler additionally fails the existing process_metrics_gate.
Valgrind reports six errors, including use-after-free in proc_stat_read.
Emitted int_to_str IR frees the allocation and returns its pointer: d as String
lowered to a pointer view, despite the source comment assuming a copy.
Resolve ownership at the cast boundary; do not hide this in the harness.
The transport probe also traps after the candidate type fix; its runtime
assertion failure remains unisolated. Do not claim a passing transport gate.

Validation of the experimental compiler: 3496 library tests passed; the new
local-tuple regression and coopmat_fill_bitwise_rhs_are_mask_consts failed.
The conformance sweep was excluded under the prior CI delegation. Full IR
determinism passed seven programs. Toolchain matrix: recommender agrees on
clang 17 and 18; multinode/giantnode skipped for missing u.data. App probe
Praetor passed; compiler directory reports existing diagnostics. No compiler
fix is retained and no implementation commit was made with failing checks.

Next: preserve typed tuple values end-to-end with native/wasm regressions;
resolve the int_to_str cast ownership contract and rerun collector Valgrind;
then validate controlled split reads, EOF, backpressure and broken-peer writes
before HTTP client parsing and one real-server journey. Update architecture
comments/contracts with the final implementation; preserve existing rationale.
No performance optimization is proposed and no timings are claimed.

Minimal compiler reproducer retained at
`tests/fixtures/load/inferred_object_tuple.bv.known-bug` (copy to a .bv path
before compiling). The incomplete experiment was removed; a final rebuild
restores the debug compiler to the preserved working source.
