# Reflection inspection preserves callable liveness

2026-10-22. Correctness prerequisite on main-based codex/reflection-liveness.
The I02 WASM codec fixture reaches an unused std/asm Prefetch wrapper, which has
no wasm32 lowering. Debugger evidence from the actual generated path identifies
txn_name=prefetch, library_mode=false, force_emit_all=false, emit_all_defns=true.
The frontend sets keep_all for every compile-time reflection, including the
physical Bytes query used by checked JSON parsing/finite-number classification.

Closed value inspections (Size, Bytes, Alignment, Type) cannot look up arbitrary
callable names. Add one specific reflection arm in the frontend liveness pass
before the existing conservative reflection fallback. Traverse the receiver so
its evaluated calls remain live. Keep the old fallback unchanged for every
unclassified target; no algorithm/type-name special cases and no new target asm.

Tests must prove each closed inspection leaves an unused callable dead, keeps
receiver effects reachable, and preserves unknown reflection's conservative
fallback. The actual native/WASM codecs then validate integration. Run the full
library baseline comparison, build and directory Praetor. Update the liveness
architecture contract and bug log with the same change. This is a correctness
fix for dead unsupported target code, not a claimed performance optimization;
I01's full runtime table remains the pre-change baseline, and I16 owns timings.
