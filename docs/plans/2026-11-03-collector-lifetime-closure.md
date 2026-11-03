# Collector lifetime closure

## Evidence

The Briev collector passes schema, unit and error-path checks after the enum
capture fix. A same-binary preflight at LOAD_PID=0, LOAD_HZ=500,
LOAD_SAMPLES=5000 produced 5000 rows and 1173 missed arrivals. RSS rose from
333 to 6541 pages; virtual bytes from 3989504 to 29691904. These are diagnostic
observations of the collector itself, not app capacity measurements.

Binary SHA256: 3bfa8df6675b8dca2e5dd4a6806f188853d7641625d70f27180ea30b3c021bf3.
IR SHA256: 81d55092c1c132d66440e38a14ee098a3a9b81ddeae3c893b72d50d01e24a7be.
Source: recommender-app/benchmarks/load/collect.bv (current working source).

Valgrind 3.15, same optimized binary, 20 samples at 100 Hz:
663 allocations / 138 frees; 8666 bytes definitely lost in 462 blocks,
90184 bytes indirectly lost in 61 blocks; 65552 bytes reachable in 2 blocks.
Loss stacks include int_to_str, read_file and proc_stat_read. No invalid-memory
access report precedes the leak summary. This establishes leaks beyond allocator
high-water retention; do not hide them with process restarts or sampler-specific
manual pointer frees.

## Source audit and next work

`global_lifetime.rs` schedules only proven heap-backed state fields, not local
returned ownership. `emit_destroy_register` frees only tracked allocation
strategies; returned values are not automatically tracked. `read_file` returns
a boxed Result containing an allocated String; the collector's parser consumes
its contents without a derived reclamation point. Typed print helpers allocate
format strings with no corresponding lifetime consumer.

Trace allocation provenance through returns, enum payloads, casts, projections,
borrows and recursive call frames. Derive ownership and last-use facts in the
frontend, with explicit consumers in codegen/stdlib. Preserve borrowed/static
values, aliases, escaping results and all public ABIs. Do not recognize helper
names or insert harness-specific frees. Unknown ownership must remain safe and
must have an explicit diagnostic/reason rather than silently claiming bounded
memory.

Start with minimized allocation/borrow/return reproductions and allocation-count
or leak gates. Before any performance optimization, capture the mandated clean
release/runtime benchmark baseline and actual-IR A/B; no timings are recorded
here. Correctness gates must cover escaping aliases, nested enums, caller-owned
images, early exits, recursion, and double-free/use-after-free under Valgrind or
ASan. Repeat the same collector geometry only after focused ownership gates pass.

Update ownership architecture documentation and BUGS.md with the proven lifetime
rules and retirement conditions. Preserve existing rationale and unrelated edits.
The collector and full load harness remain unfinished while this gate is open.

First minimized gate: a variant-tag predicate with an inline object payload
allocates even for Present(_). The native allocation-counter fixture fails at
O0 with exit 3 (allocation observed), while both tag decisions are correct.
The binding emitter materializes the payload before seeing that no name is
bound. Skip binding emission only when every subpattern is a wildcard (including
zero payloads); retain existing tag-condition and named-binding paths. This
closes discarded-copy leaks but is not the general ownership fix.

Discarded-payload checkpoint: native allocator regression passes at O0/O3;
3,438 library tests pass with only the delegated conformance sweep excluded;
build has no new warnings; 11/11 native load fixtures pass; seven-case full IR
determinism passes. Clang 17 recommender passes; two dataset-dependent matrix
rows skip explicitly because u.data is absent. Praetor finds no new diagnostic
category: existing bind_pattern complexity stays 28; its existing length warning
increases from 166 to 172 lines. New integration test has no diagnostics.
