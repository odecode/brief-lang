# fix(llvm): preserve returns after guarded tail recursion

## Summary

A recursive `term` inside a `when` branch could leave the emitter's tail-backedge flag set when emission continued along the guard's false path. A later terminal call then lost its return instruction, and the function received a fallback return of zero.

This caused the wasm float formatter to display `0 / 5 predicted` for valid recommender scores. The fix clears the backedge flag at the guarded merge, alongside the existing termination-state reset.

## Symptom and minimal reproduction

The app received valid prediction scores, but converting them to text in the browser produced zero. A literal `4.5 as String` reproduced the issue without involving the backend response or recommendation algorithm.

The smaller compiler regression has this control flow:

```briev
defn identity(value: Int) -> Int { term value; };

defn descend(n: Int) -> Int {
    when n > 0 { term descend(n-1); };
    term identity(7);
};

let answer: Int = descend(2);
```

`term` returns a value from a Briev function. While `n > 0`, the recursive call is lowered to a loop backedge. Once the condition is false, execution reaches `identity(7)` and must return its result, 7.

The faulty emitter treated that later terminal call as though it had already emitted a backedge. It emitted the call but discarded the result.

## Evidence isolating the cause

Three observations narrowed the failure to code generation:

1. The browser protocol accepted a decoded score of 4.5, and a literal 4.5 also formatted as zero. Score calculation and transport were not required to reproduce it.
2. Native formatting produced 4.5. In the wasm IR, `frac_all_digits` called `frac_digit_loop` and then returned literal zero; the native IR returned the call's result.
3. Restoring the original float formatter while retaining this backend fix still produced `4.5 / 5 predicted`. The experimental formatter rewrite was unnecessary and is not included.

The decisive IR difference was:

```llvm
; Faulty wasm shape: discard the call result.
%digits = call i64 @frac_digit_loop(...)
ret i64 0

; Required shape: return the computed digits.
%digits = call i64 @frac_digit_loop(...)
ret i64 %digits
```

The register name and omitted arguments above are normalized for readability. The observed fault was the literal-zero return following the digit-extractor call.

## Root cause

The backend records whether a terminal recursive call emitted a loop backedge in `tail_loop_backedge`. The terminal-call handler in [`src/backend/llvm/emit_stmt.rs:1969`](https://github.com/odecode/brief-lang/blob/f30520c7/src/backend/llvm/emit_stmt.rs#L1969) skips another return when that flag is set. That is necessary on a path which already branches back to the loop header.

Guarded-statement emission then writes the continuation block. Before this fix it reset only the general termination flag:

```rust
backend.fun.terminated = false;
```

It left `tail_loop_backedge` inherited from the guarded body. The continuation represents the false path, which did not execute that body or take its backedge. A later `term` consulted the stale flag and skipped its return. The function's fallback return then supplied zero.

## Fix and why it is sound

Reset both pieces of path-dependent termination state at the guarded merge:

```rust
backend.fun.terminated = false;
backend.fun.tail_loop_backedge = false;
```

The added reset is at [`emit_stmt.rs:2234`](https://github.com/odecode/brief-lang/blob/f30520c7/src/backend/llvm/emit_stmt.rs#L2234).

The recursive branch's backedge has already been emitted. Clearing the bookkeeping flag does not change that instruction. It describes the continuation currently being emitted, which must be allowed to produce its own terminal return.

This restores a general control-flow invariant: termination state from one branch must not suppress a return on another reachable path. No float formatter, recommendation score, or specific function name is recognized by the fix.

## Regression test

[`guarded_tail_backedge_does_not_swallow_later_return`](https://github.com/odecode/brief-lang/blob/f30520c7/src/backend/llvm/crash_regressions.rs#L206) parses and checks the minimal Briev program, then emits wasm32 LLVM IR. It verifies that:

- the recursive function actually uses tail-loop lowering;
- the later call to `identity` is emitted;
- the function does not receive the erroneous `ret i32 0` fallback.

Checking that tail-loop lowering occurred prevents the regression from passing merely because the optimizer stopped exercising the failing path. The app browser fixture supplies a separate end-to-end check of visible formatting behavior.

## Verification and limits

On this clean branch, based on upstream `373e548e`:

```text
cargo test --lib guarded_tail_backedge_does_not_swallow_later_return
1 passed; 0 failed
```

On the integration tree, the compiler and standalone app were rebuilt. The browser interaction fixture verified displayed predictions of **4.5** and **4.4**, alongside the existing selection and event-handling checks.

The final integration library run reported **3,422 passed and 11 failed**, with only the conformance sweep pending. The failures were the accepted SPIR-V environment cases. The user requested cancelling the local sweep and leaving it to origin CI. The full suite is therefore not reported as locally green, and the integration run is distinct from the isolated branch check above.

## Merge order and files

Branch: `fix/guarded-tail-return`; commit: `f30520c7`; base: upstream `373e548e`.

This PR is independent of [the concrete bit-cast fix, #55](https://github.com/Randozart/briev-lang/pull/55). Either can merge first. Both append to `BUGS.md`; retain both diagnoses if that produces an append conflict.

The four changed files are `src/backend/llvm/emit_stmt.rs`, its regression in `src/backend/llvm/crash_regressions.rs`, `BUGS.md`, and [`docs/architecture/guarded-tail-returns.md`](https://github.com/odecode/brief-lang/blob/f30520c7/docs/architecture/guarded-tail-returns.md). There is no app workaround, float formatter rewrite, or unrelated integration code in this PR.
