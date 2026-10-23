Browser imports previously pulled native process/syscall lanes into casting and
formatting. Extract the shared portable implementation, select a browser prelude,
keep fixed-width decimal arithmetic explicit, and add JSON encoding with Unicode,
finite-number and nesting checks. Preserve GET and add HTTP verb/body helpers,
owned WebSocket handles and cancellable event timers. Close read_file's owned
descriptor on both result paths.

The branch includes the existing strict JSON parser and flat Matrix/Vector
module prerequisites because they are absent from main. Merge their existing
stdlib feature/fix PRs first; overlapping source is the verified integration
version. No compiler source changes are included. Compiler prerequisite:
fix/wasm32-web-runtime plus the existing generic-call/collection fixes.

Validation: native JSON round trips, actual WASM Int32/Unicode/nested JSON,
512 reads under RLIMIT_NOFILE=64, HTTP verb/error handling, per-channel FIFO,
limits/isolation/closure and timer cancellation. Combined native server and
Chrome application gates pass. Final library and environment-baseline results
are recorded in the tracked plans.
