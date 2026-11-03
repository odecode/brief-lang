# Enum result pointer capture correctness

The streaming collector reports corrupted page/tick units at O3 while O0
reports the independently queried `getconf PAGESIZE=4096`, `CLK_TCK=100`.
This is correctness work, not a performance optimization.

Pre-build experiment on the actual generated `collect.ll`:

| IR variant | Page bytes | Clock ticks/s |
|---|---:|---:|
| Original, O0 | 4096 | 100 |
| Original, O3/LTO | 11 | stack-address-sized integer |
| Replace argmem effects with general memory effects, O3/LTO | 11 | corrupted |
| Remove noalias only, O3/LTO | 11 | corrupted |
| Remove nocapture only from enum_out, O3/LTO | 4096 | 100 |

O3 experiments use clang-17 -O3 -flto -march=native -ffast-math
-fdata-sections -ffunction-sections -Wl,--gc-sections with the generated IR,
lib/runtime/briev_rt.c, -ldl -lm. No timings are claimed. The broader memory
effect hypothesis was refuted and does not license a change.

`emit_toplevel.rs` emits `ptr noalias nocapture align 8 %enum_out`, while
`helpers.rs` returns that pointer as an integer handle. Returning the address
captures it under the LLVM 17 contract. Remove only the invalid attribute at
the single enum-result signature emitter. Keep the existing caller-owned ABI.
Audit all enum_out sites, update the old signature assertion, and add a native
OS-value regression comparing Briev units against independent getconf values.

Validation: focused regression, library suite excluding delegated conformance,
build, native load fixtures, determinism and toolchain gate. Update architecture
capture documentation and BUGS.md; preserve prior rationale and unrelated work.
Reference: https://releases.llvm.org/17.0.1/docs/LangRef.html#parameter-attributes

Validated: the focused optimized OS-value integration passes; 3,438 library
tests pass (delegated conformance excluded); build completes without warnings;
all 11 native load fixtures and all app load gates pass. Full seven-case IR
determinism is green. Clang 17 matrix runs recommender successfully; two
dataset-dependent rows are explicitly skipped because u.data is absent.
The collector's schema and failed-read checks pass after the fix. A separate
5,000-sample preflight found lifetime leaks, tracked separately; the capture
fix does not establish bounded-memory collection.
