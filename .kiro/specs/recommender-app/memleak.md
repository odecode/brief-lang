# Collector memory leaks

Recorded 2026-11-04.

## Current status

Fixed in the working checkout on 2026-11-04. All nine native Valgrind cases pass
with zero definite/indirect loss and zero memory errors. Two 5,000-sample runs
at 500 Hz have flat RSS and virtual memory after warmup. The completion record
below supersedes the original failing observations, which are preserved here.
Application capacity and sustained backend campaigns remain unmeasured.

## Scope and locations

The application repository is C:/Users/wotto/code/recommender-app.
The compiler and standard library repository is C:/Users/wotto/code/briev-lang.

Application files involved are

- benchmarks/load/collect.bv, the process-metrics collector
- benchmarks/load/check-memory.sh, the native Valgrind gate
- benchmarks/load/probes/file_read_lifetime.bv, the isolated file-result probe
- target/load-memory/, generated executables, output and Valgrind reports

Compiler investigation records are

- docs/plans/2026-11-03-collector-lifetime-closure.md
- docs/plans/2026-11-04-collector-output-lifetimes.md

## Observed behavior

An initial 5,000-sample run at 500 Hz grew from 333 to 6,541 RSS pages.
Valgrind subsequently confirmed definitely and indirectly lost allocations.
This establishes a reclamation defect beyond allocator high-water retention.
These measurements describe the collector process itself.

Allocation stacks identified decimal formatting, file reads, parser scratch
storage and fresh observation objects. Fixing integer output reduces leakage
but does not bound the collector's memory use.

### Integer-output fix

The native print_int implementation previously created an owned decimal string
and passed it to a borrowing output writer. The temporary survived each call.

PR #60 streams digits into the existing stdout buffer. It handles zero, both
signs and the minimum signed integer without allocating a decimal string.
The string-returning conversion API retains its existing behavior.

A native regression warms stdout, prints 2,048 signed-extrema pairs, verifies
79,873 output bytes and checks that live allocation count returns to baseline.
The isolated print fixture has zero lost bytes under Valgrind. The clean
carve-out passed 3,441 compiler library tests.

A controlled collector IR experiment that released only the decimal temporary
reduced directly lost allocations from 462 to 121 over 20 samples. Indirect
losses remained, demonstrating independent lifetime defects.

PR https://github.com/Randozart/briev-lang/pull/60

### File-result regression cases

The permanent application memory gate was introduced in commit 5bf6251 and
expanded in ab55fd1. It builds the probe and collector and checks them with
Valgrind. Exit 91 identifies memory errors or definite/indirect leaks.

The probe exercises one and twenty reads for each of these cases

| READ_MODE | Operation |
| --- | --- |
| 0 | Read /proc/self/stat |
| 1 | Read a 20,000-byte file crossing the initial 4,096-byte capacity and subsequent growth boundaries |
| 2 | Open an invalid path beneath an ordinary file |
| 3 | Open /proc/self as a file and encounter a read failure |

The script creates the growth input at target/load-memory/growth-input.

Measured twenty-read results include

| Case | Definitely lost | Indirectly lost |
| --- | --- | --- |
| Large successful reads | 320 bytes in 20 result containers | 655,520 bytes in 20 payload buffers |
| Open failures | 320 bytes in 20 result containers | 0 bytes |

All eight file cases and the collector case currently fail the memory gate.
The script also checks probe completion output and the collector's 19-column,
20-sample CSV output. A failed memory verdict must remain visible even when
functional output is correct.

## Lifetime analysis

The standard library implementation is lib/std/os/fs.bv.

read_file converts its path to a C string, opens the file and releases the path
temporary. It then allocates an initial string buffer and delegates to
read_whole. The wrapper closes the file descriptor after that call.

read_whole doubles the buffer when full and releases the replaced buffer.
On read failure it releases the active buffer and returns Err. On EOF it
writes the string length and returns Ok containing the string handle.

The returned Result image and its active payload have separate lifetimes.
Successful reads retain both the container and the final string buffer.
Open failures retain a container even though no file-content buffer exists.

The current lifetime machinery does not derive complete reclamation for these
local returned values. global_lifetime.rs handles selected heap-backed state.
emit_destroy_register relies on tracked allocation strategies, which do not
provide complete provenance for returned containers and nested payloads.

The existing destination-ownership analysis is a starting point, but its
representation and escape facts must not be treated as a complete proof of
allocation ownership or permission to free a payload.

## Controlled diagnostic experiments

An isolated successful file-read experiment released the result container and
string after their observed last use in generated LLVM IR. At both one and
twenty reads it removed definite and indirect loss with identical output and
zero invalid memory accesses.

A broader successful-path experiment on actual collector IR released

- Temporary pathname strings after the file read
- File-result images and strings after parsing
- Parser list backing storage and headers after copying counters
- Fresh observations, contained process-stat objects and batches after output
- Startup auxiliary-vector storage after its last lookup

The control and experiment used the same optimized O3/LTO link configuration.

| Measurement | Control | Experimental releases |
| --- | --- | --- |
| Direct loss over 20 samples | 3,576 bytes in 121 blocks | 0 |
| Indirect loss over 20 samples | 90,112 bytes in 60 blocks | 0 |
| RSS pages at sample 1 of 5,000 | 354 | 366 |
| RSS pages at sample 5,000 | 5,954 | 366 |

Both emitted 5,000 valid sample rows. The experiment reported zero Valgrind
errors. These manual IR edits establish the allocation sources and successful
last-use points. They have not been shipped as production reclamation.

## Required production fix

Derive allocation ownership and last-use facts in the frontend and consume them
in code generation. The mechanism must apply to ordinary Briev programs,
including user-defined types and helpers.

Track container ownership independently from active payload ownership. Follow
allocation provenance through returns, recursive calls, casts, projections,
aliases and enum construction. Account for backing storage replaced during
buffer growth.

A release requires proof that storage is owned, remains live until that point
and has no escaping alias requiring a longer lifetime. Preserve static and
borrowed payloads, caller-provided result destinations and values transferred
to another owner. Unknown provenance must remain conservative.

Do not insert raw frees into the collector, recognize helper names in the
compiler, or restart the collector to conceal growth.

Update compiler ownership architecture documentation and BUGS.md alongside
the implementation. Upstream PR descriptions must explain the Briev constructs
and include self-contained examples understandable without this application.

## Verification required before completion

- Small and growing file reads, open failure and read failure
- Returned and escaping aliases, including an alias used after the original result's last use
- Static and borrowed payloads
- Nested enums and caller-owned result images
- Recursive returns and early exits
- Repeated valid alias use without double-free or use-after-free
- Allocation and leak checks under Valgrind or ASan
- The full collector memory gate and a repeated 5,000-sample run
- Required compiler library, native and wasm regression checks

The original expanded probe covered file success, growth and failure paths.
The completion record below includes alias, borrowed-payload and
caller-destination safety gates added during the repair.

## Additional finding

While expanding the probe, a nested get_env_int! invocation reached codegen as
an unresolved plugin-intercept call and caused a compiler panic. The current
probe read READ_MODE into a named binding. This compiler gap is now fixed with
the shared exhaustive postorder AST visitor and native/unit regressions.

## Running the existing memory gate

Run from the application repository in WSL with explicit compiler and source
paths. Use a compiler containing the collector's prerequisite fixes.

```sh
BRIEV_ROOT=/mnt/c/Users/wotto/code/briev-lang \
BRIEVC=/path/to/compatible/brievc \
bash benchmarks/load/check-memory.sh
```

Inspect target/load-memory/*.valgrind, *.stdout and *.build.log.
The expected outcome with the repaired compiler is a passing memory gate.
Earlier diagnostic IR experiments alone did not establish production safety.

## Completion record — 2026-11-04

Frontend call-region proofs now follow allocation identities through calls,
returns, casts, raw memory, aliases, independent object fields and active enum
variants. Incoming storage is borrowed independently of fresh allocations at
the same allocation site. The native consumer tracks actual allocator results
and releases them at proved nonescaping call boundaries. It handles explicit
free/realloc, growth failure and suspended tracking; borrowed/static payloads
and caller result images are not registered as allocations. Unknown effects
remain conservative. No raw frees or helper-name recognition were added to the
collector. See `docs/plans/2026-11-04-collector-reclamation-closure.md` in Briev.

The initial heap repair exposed linear stack growth from inlining region frames
into recursive sampling. A controlled generated-IR A/B isolated this cause;
separate proved scope calls preserve bounded tail execution. A missing LLVM
attribute-group declaration and ID collision were fixed as part of that closure.

`check-memory.sh`: all eight file cases (small/growing/open/read failure,
one/twenty reads) and the 20-sample collector pass. Every case has zero
definitely/indirectly lost bytes and zero Valgrind errors. The only remaining
reachable allocation is the 65,536-byte process-lifetime stdout buffer.

Two independent self-sampling runs use `LOAD_PID=0 LOAD_HZ=500 LOAD_SAMPLES=5000`:

| Run | Valid rows | First/last RSS pages | RSS range after row 1,000 | Virtual bytes after row 1,000 |
| --- | ---: | ---: | ---: | ---: |
| 1 | 5,000 | 323 / 355 | 355–355 | 3,989,504 constant |
| 2 | 5,000 | 346 / 378 | 378–378 | 3,989,504 constant |

All rows have 19 columns, successful reads, ordered bracket/deadline timestamps,
4,096-byte pages and 100 clock ticks/second. Raw CSV and summary are in the app's
`target/load-memory/preflight-5000-{1,2}.csv` and `preflight-summary.json`.
The full load functional gate also passes scheduling, attempt accounting,
process observations, collector schema and failed-read status.

Compiler SHA-256: `d2582dd65100673fd48f4f6c976a7e6dfb7668356b939a444fac162f522875ff`.
Collector SHA-256: `285f48f0c08b327b499bacd0ee7027300e3992db856da8f7fbbeaeda375eb37a`.
These are memory-correctness results for the current working tree, not a
capacity measurement or a claim of universal reclamation on every target.

Final compiler validation: 3,459 library tests pass, with only the previously
delegated full source conformance sweep excluded. Native alias/allocator,
integer-output, discarded-payload and nested-environment gates pass. Both wasm
integration gates pass, including the full collection/JSON fixture corpus.
Full IR determinism passes all seven programs. Build passes without new warnings.
Kani harnesses were added, but Kani cannot execute on the WSL glibc version;
they are not claimed proved. The toolchain matrix passes its available LLVM 17
row; two data-dependent programs are skipped because `u.data` is absent.
