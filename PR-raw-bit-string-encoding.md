# Restore raw-bit String encoding and consistent cast widths

Casting a raw `Bits<N>` buffer handle to String lost its encoding constructor
when Data-to-String became a representation-preserving cast. Restore a direct
Bit-category encoding edge so that conversion constructs owned String storage,
while Data-to-String continues to preserve an existing representation.

The executable reproduction also exposed invalid LLVM for String-to-Bits casts:
the pointer was relabelled as an integer without conversion. Concrete bit casts
now emit ptrtoint and use zero extension when widening raw integers. Constructor
calls use the source width for pointer conversion and adapt custom constructor
arguments to their i64 boundary ABI.

The tuple regression was asserting an obsolete ABI. Upstream f5bb16e6e made
tuple handles target-width; the replacement checks matching definition, call,
and consumption on wasm32 and x86_64 while retaining i64 tuple storage slots.

Validation: native String/Bits/String and String/Data/String output `hello`;
browser fixture verifies both routes, widening and tuple return/destructuring.
The standalone recommender builds and passes its full browser interaction
fixture, including prediction scores. All seven formerly failing non-SPIR-V
tests pass in the final library run. Final full-suite status is recorded in
docs/plans/2026-11-03-cast-and-tuple-regressions.md.

Based on the current integration tree; preserve the prior Data representation
cast from 894fcfa5 and the target-width tuple ABI from f5bb16e6e when carving out.
