# Module metadata allocation prerequisite for I06

2026-10-22. The recommender server fails LLVM verification because type TBAA
metadata and StateAliasScope both define !99. Type, range, and loop metadata
currently assume disjoint fixed numeric ranges; program size invalidates that
assumption. This is a correctness fix, not a performance optimization.

Reserve the deterministic TBAA prefix, then allocate every generated metadata
node from one CompilerContext counter. Keep pending definitions at module scope
so function reset/snapshot operations cannot erase them or rewind allocation.
Reset module metadata at each emission/fixpoint round. Preserve the existing
aliasing semantics and rewrite rationale comments to explain the shared lifetime.

Verify uniqueness with a universe larger than both historical reservations,
range/loop metadata, and function resets. Run focused backend tests, rebuild the
release compiler, and build the real server and loop gate with clang. Final
library failure-name comparison and backend determinism gates precede commit.
Update backend architecture and BUGS.md in the same logical fix. Then resume
the I06 experiment and active-view implementation.
