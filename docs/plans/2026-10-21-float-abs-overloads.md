# Float Abs overload correctness

The final task-12 cached-prediction comparison exposed an undefined
`@llvm.fabs.float` call. LLVM's overloaded intrinsics use width suffixes f16,
bf16, f32 and f64, not the textual operand types half/bfloat/float/double.

Add an overload-aware Abs template seam before the unchanged legacy template
fallback, and declare the two narrow fabs overloads alongside existing f32/f64
declarations. Preserve integer Abs and all other operation templates. This is
an intrinsic correctness fix, with no performance claim or shape recognition.

Tests: all four representations' emitted names and the integer/unknown fallback;
native Float32/Float64 and integer control; the server's cached/full-engine
comparison. Isolated branch fix/float-abs-intrinsic is prepared from main.
Update backend architecture commentary and BUGS.md with evidence. No interpreter
changes, per explicit user instruction. Commits remain pending workflow approval.
