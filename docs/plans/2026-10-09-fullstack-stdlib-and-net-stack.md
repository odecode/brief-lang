

## Result wrong-side unwrap fabricated payloads (FIXED 2026-10-21)

unwrap and unwrap_err fabricated cast fallback values instead of their documented
trap. Wrong sides now trap; actual payloads are preserved. Standalone regression
tests/fixtures/stdlib/result_object_gate.bv passes both object payloads and both
wrong-side SIGILL paths on integration. Depends on compiler fix 23cbbdac; this
stdlib branch carries no compiler changes. Integration build passes; library
suite: 3164 passed, 38 baseline failures, no added failure names. Praetor passes.
