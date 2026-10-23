# Trap on wrong-side Result unwraps

unwrap(Err(...)) fabricated `0 as T`; unwrap_err(Ok(...)) fabricated
`"aborted" as E`. This contradicted the documented trapping API and produced
invalid values for object payloads. Both wrong-side branches now trap; valid
branches return the original payload. Root locations: lib/std/result.bv:23, :33.

Standalone tests/fixtures/stdlib/result_object_gate.bv verifies both object
payloads. Running with UNWRAP_MODE=1 and =2 separately verifies SIGILL (132) for
both wrong-side calls. Verified with the integration compiler. Cargo build passes;
integration library suite: 3164 passed, 38 baseline failures, none added.
Praetor passes. No app or PostgreSQL changes are included.

BASE: upstream main. MERGE ORDER: the separate compiler fix
fix/match-terminating-arm-values (23cbbdac) must land first. Native compilation of
the trapping matches depends on it; this branch carries no compiler source.