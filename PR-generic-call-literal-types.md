# Preserve inferred collection types for generic literal arguments

## Problem and discriminator

An inline String-list argument to a generic function emits invalid LLVM:
a pointer-valued element is stored as i64 without conversion. This blocked
PostgreSQL result decoding at `fields + [text]` and `fields + [""]`.

The controlled probes isolate the trigger without PostgreSQL: a standalone
List<String> literal works, and List<Int> concatenation works, while String
concatenation with an inline singleton failed native compilation. After this
fix, the same String probe compiles and prints four true checks for length,
first element, appended text, and appended empty string. The Int control
continues to print two true checks.

## Root cause and final implementation

Generic call codegen constructs literal arguments from the callee's declared
parameter type before specializing the call. Using raw List<T> at that point
loses the element representation, although call checking inferred T=String.

`src/typechecker/call_literals.rs:17` reuses generic-call inference and
substitution to preserve each literal argument's inferred collection type as an
ordinary typed value block. The block remains at the original argument site;
there is no effect hoisting or duplicated evaluation. Its internal binding name
contains a dot and cannot be spelled as a source binding identifier.

The shared elaboration wrapper (`src/typechecker/mod.rs:2893`) handles both
authored generic calls and calls synthesized by operator elaboration. This
covers declared collections generally, without recognizing function or element
type names. Existing collection constructors and backend ABI paths are unchanged.

Elaboration also initializes the enclosing declared-return context for defns and
txns (`src/typechecker/mod.rs:2780`, `:2800`), matching ordinary typechecking.
That context is necessary for empty tuple accumulators such as enumerate/zip;
otherwise revisiting their calls incorrectly infers List<Int>.

## Tests and verification

Regression tests cover operator-generated String calls (parameter and empty
literal), direct generic literal calls with first-argument inference, Int
controls, nested collections, and empty tuple accumulators in defns and callable
txns. Existing interpreter, package, and conformance tests remain enabled.

Human-run verification after the final correction:

- Focused typechecker suite and list_plus_list checks: green.
- Full cargo test --lib: reported green.
- Debug compiler build and native Int/String concatenation probes: passed;
  String prints four true checks, Int prints two true checks.
- Praetor before/after comparison: no added diagnostics or increased metrics.
  The original 103-line walker's existing diagnostic follows its rename to
  elaborate_expr_children; the new module has no diagnostics.
- git diff --check: passed.

The full PostgreSQL schema-gate rebuild remains a downstream integration check,
requiring the integration branch's other compiler fixes. It is not claimed as
verified by this isolated PR.

## Scope and merge order

Branch fix/generic-call-literal-types is based on main and contains only this
compiler fix, its regression tests, and related documentation. No application or
stdlib feature files belong to the commit. This fix has no dependency on the
relative-import or pointer-provenance fixes; the full schema gate needs all
applicable fixes together on integration/ptr-provenance. The human submits and
merges the PR; the feature vessel receives fixes through upstream main per
WORKFLOW.md.
