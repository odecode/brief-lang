# Complete print expansion traversal

2026-10-22. Separate main-based prerequisite `codex/print-traversal`.
The I02 worker fixture's diagnostic `foreach ... { when ... { println!(...); }; }`
reaches LLVM as an unresolved PluginIntercept. The print plugin only walks
guarded statement bodies and a partial expression set. This is a frontend
coverage defect, not a reason to remove the fixture diagnostic.

Add a centralized exhaustive mutable postorder AST visitor, corresponding to
the existing read-only visitor. Print expansion uses that visitor so every
statement, expression, pattern, contract and behavioral member receives the same
coverage. Expand nested arguments/receivers before replacing their parent;
preserve the existing format parser, dispatch through Print#, and all rationale.
Remove the obsolete partial print walkers/type-collection plumbing: print
expansion is type-independent and Print# owns typed dispatch.

Tests cover nested foreach/guard diagnostics and macros in previously skipped
containers/operands, no unresolved print intercepts, postorder exactly-once
mutation, and malformed nested format diagnostics. Run existing print tests,
full library comparison, build, changed-directory Praetor and native/WASM
contract gates. Update architecture visitor contract and BUGS.md together.
No performance optimization or timing claim; I01's complete runtime baseline
remains the pre-change evidence, I16 owns responsiveness acceptance.
