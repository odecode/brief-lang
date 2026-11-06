# Add checked native measurement primitives

Add four stdlib modules for programs that measure elapsed time, observe Linux
processes or aggregate bounded latency distributions:

- `std/os/time.bv`: checked monotonic timestamps, explicit clock errors, and
  nanosecond overflow checks. `now_ns` keeps its nonnegative contract by trapping
  if time is unavailable; `clock_ns_res` exposes a recoverable Result.
- `std/os/proc_stat.bv`: `/proc/PID/stat` parsing with PID/start-time identity,
  CPU ticks, page faults, threads, virtual bytes and resident pages. Malformed
  required fields and integer overflow return errors.
- `std/os/auxv.bv`: query page size and clock-tick frequency from Linux auxiliary
  vectors instead of assuming platform units. Missing, malformed and duplicate
  entries are rejected.
- `std/stats/histogram.bv`: fixed-size mergeable bins with count, overflow and
  maximum. Quantiles use nearest rank and declared bin upper bounds; merge bins
  before calculating quantiles.

For example, a process observer can bracket `proc_stat_read(pid)` with `now_ns()`
and use `process_units()` to interpret ticks/pages. Consumers must compare both
PID and start time before subtracting counters. RSS is approximate resident
memory, not unique or private memory.

Four executable fixtures cover failed clock reads and elapsed sleep, synthetic
and live process records, binary auxiliary vectors and real host units, and
histogram distribution/merge/overflow behavior. The native integration test runs
all four and compares expected output. Architecture docs describe each API and
its limits. No compiler changes or application code are included.

The feature builds independently from main 3737396b. Repeated file sampling
additionally needs `fix/read-file-descriptor-lifetime`; the combined collector
verification passes functional gates, nine Valgrind cases and two independent
5,000-sample self-observations. Those establish collector correctness and bounded
memory, not backend capacity or throughput.

Final repository verification is recorded in
`docs/plans/2026-11-05-collector-prerequisite-carveout.md`.

Final verification: 3,499 library tests passed with zero failures (the previously
delegated source sweep remains with CI), all four native fixtures passed through
the integration test, cargo build completed without warnings, and Praetor passed
all changed code directories. This is commit c403e943. The independent descriptor
cleanup is [PR #63](https://github.com/Randozart/briev-lang/pull/63).
