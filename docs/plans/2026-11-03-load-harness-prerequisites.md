# Load harness stdlib prerequisites

2026-11-03. Parent execution plan lives in recommender-app/docs/plans/2026-11-03-briev-native-load-harness.md.

Scope: correct native timing, bounded mergeable statistics, incremental HTTP
client response parsing, WebSocket client lifecycle and process observation.
No compiler optimization is proposed. Full runtime performance baseline remains
unmeasured and is required before any optimization change.

Current work: checked clock API preserves now_ns nonnegative contract; invalid
clock and elapsed-time gate passes with cached compiler. Source-matched release
build and cargo test --lib are in progress. Existing compiler working changes
must remain intact. New histogram fixture checks known distribution, overflow
and merged quantiles; failing native result under investigation, no workaround.

Validation: source-matched native fixtures, interpreter comparison for pure
statistics, cargo test --lib, cargo build, Praetor changed directories. For
compiler fixes add minimized reproductions and relevant backend/determinism gates.

Documentation: native-timing.md records error/overflow semantics; add statistics
API documentation with validated results. Append discoveries to BUGS.md without
staging unrelated edits. Preserve rationale provenance during refactors.

Database audit: dedicated briev_load role/database created via authorized
PostgreSQL administration. Existing server supports only trust auth; password
challenge support is a separate identified stdlib gap. No global authentication
configuration changed.

2026-11-03 validation steering: user explicitly delegates the long-running
conformance_sweep_every_active_source_parses_and_checks test to upstream CI.
Local completion uses focused gates and the remaining library tests; do not
wait for or claim a local pass for the delegated sweep.

Local baseline limitation: the pre-change library test artifact reports SPIR-V
validator failures. Isolated reproduction test_scale_kernel_passes_spirv_val:
"Invalid SPIR-V binary version 1.6 for target environment SPIR-V 1.5."
This is not a passing library suite; keep the limitation visible. The focused
indexed-write library fixture must define its own coll type because
library::parse_and_check does not load the native prelude. CLI fixtures retain
real stdlib List coverage.

Native validation update: dynamic List indexed stores, nested fields, a custom
heap collection, and histogram distribution/merge now pass via the CLI. The
self-contained fixed-size user collection regression passes O0 and O2. Its
expansion exposed inline aggregate read/copy and native element-width bugs;
those paths now preserve storage identity and use resolved layout widths.
Bare inline member term has a scoped exit, and member scalar parameters use
the existing coercion helper. inline_member_term_gate verifies both guarded
branches return to the caller. Bounds integration and latest full-suite checks
remain pending; these are correctness results, not performance measurements.

Validation checkpoint: 3,437 library tests passed with the conformance sweep
excluded as requested. Five native measurement fixtures and clock/bounds
integration passed, followed by the live process-stat fixture. A locally built
SPIRV-Tools validator and disassembler removed the installed tool-version
limitation. No compiler warnings were reported by the matching debug build.

The wider suite exposed invalid dynamic-dispatch phi predecessors after inline
member exits. Dispatch now records the actual ending block. Two existing IR
assertions also compared function-local register names across separate functions;
their checks now run within each emitted function rather than mistaking unrelated
stores for writes to the same register.

Additional storage coverage is in progress: fixed collections of records,
pointers and partially initialized elements. The first record fixture found
that callable pointer types were incorrectly reused as inline storage types.
Constructor, member and array access paths now share explicit array element
storage and image-copy helpers. The fixture and full library suite must pass
again before this broader change is considered validated. Pointer boxing also
gets a 32-bit address-bit preservation test.

Committed independent increments: checked native timing (`a8434136`) and Linux
process-stat parsing (`0930adc8`). App commits implement fixed-rate scheduling
and bracketed process observations with identity/reset/overflow validation.
Network journeys, database challenge authentication and long-run collection
remain implementation work. No capacity or performance result has been claimed.

Native storage checkpoint: 3,438 library tests passed, with only the delegated
conformance sweep filtered out. Seven native load fixtures passed; the effects
fixture additionally checks direct SetAt calls. Fixed element coverage includes
records, objects, pointer handles, Strings and omitted zero initialization.
Praetor comparison exposed increased complexity in pointer boxing; the new
width conversion is extracted into a helper before the final verification.
These remain correctness checks, with no timing or capacity claim.

Final native compiler checkpoint: 3,438 library tests passed again after the
helper extraction (127 seconds; conformance sweep excluded). Matching debug
build completed without warnings. Clock and bounds integration passed. All
seven determinism corpus cases were byte-identical in independent processes.
Praetor pointer-boxing complexity is back to the pre-change baseline; its new
helper adds no diagnostic. Interpreter parity remains a separate open gate.
