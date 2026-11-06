# Recommender pending authentication state

2026-10-28. Investigate and repair login requests that never receive a reply.

Generated `server.ll` calls `server_step` but drops its return: whole-object
assignment to a pooled top-level object has no lowering. Restore the general
boxed-value-to-pool publication path using the existing initialization helper.
The existing mixed-field reactor replacement regression must execute at O0/O2.
Check boxing field widths as well, since packed Bool/Float slots must retain
adjacent members. Remove temporary app instrumentation and restore its original
service contract. Verify native login rejection, registration, login and session
state, then cargo test --lib/build and Praetor. Document the cause in BUGS.md
and architecture comments; preserve prior rationale. This is a correctness fix,
so benchmark timing is not an acceptance gate.

## Investigation results

The causal commit is the merge `5c2ec29c`, not `fba17b79`. Its diff against its
first parent removes the whole-object publication arm and changes the helper's
visibility back to private. The recovery fix in `894fcfa5` had both pieces.
The strengthened fixture must declare an object member so the compiler registers
pool columns; a methodless object remains a boxed handle and missed the bug.
Use syscall exit codes for failure checks: endprogram's integer expression is
not a process exit status. The old release compiler exits 72 on the pooled case.

## Acceptance results

The restored compiler's server returned: invalid login 401 (0.110 s), register
200 (0.303 s), login 200 (0.103 s), and a subsequent authenticated state GET 200
(0.003 s). The strengthened pooled-object regression passes at O0 and O2.
The original test was ineffective: its methodless object did not use pool columns,
and endprogram integer expressions did not assert a process failure. The revised
test uses an object member, an initializer function, an open-ended reactor and
SysCall# failure exits; the old compiler exits 72, the repaired compiler exits 0.
Temporary diagnostics and the experimental service postcondition were removed.

The full `cargo test --lib` run reported 14 failures (casting/Bit-to-String,
wasm32 tuple return ABI and SPIR-V gates). Its remaining conformance sweep was
stopped after roughly ten minutes. It is not a green per-commit gate; changes
remain uncommitted. Praetor still reports the existing oversized assignment
emitter and other backend baseline diagnostics. The focused pooled-object gate
and HTTP authentication acceptance are green.

Final release build passed with no Rust warnings. Rebuilt and relaunched backend:
invalid login 401 (0.108 s), register 200 (0.103 s), login 200 (0.102 s), later
session state 200 (0.002 s). Frontend app.html serves HTTP 200 at port 8081.
PostgreSQL, backend (8080) and frontend (8081) remain running for manual use.
