Fix floating `Abs#` calls that fail native linking with undefined
`@llvm.fabs.float` or `@llvm.fabs.double`. LLVM overload names use width suffixes,
while operands keep their normal LLVM type spellings.

An additive overload-aware template seam handles f16/bf16/f32/f64 before the
unchanged legacy fallback. The narrow fabs declarations join existing f32/f64
declarations. Integer Abs and all other intrinsic templates are unchanged.

Two unit tests check all four floating overloads and integer/unknown fallbacks.
The native fixture verifies Float32, Float64 and an integer control. The task-12
cached predictor then builds/runs and agrees with the full CF engine after
refresh, with finite-value checks before numeric tolerance comparison.

This fix is prepared on fix/float-abs-intrinsic from main. Merge it alongside
collection-assignment-rebind before the app-only recommender-server feature.
No interpreter changes. See the float-abs-overloads plan and BUGS.md for the
source-level diagnosis, verification and provenance.
