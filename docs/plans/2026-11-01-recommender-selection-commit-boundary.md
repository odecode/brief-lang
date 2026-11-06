# Selection commit boundary — 2026-11-01

The human still observes lag with the verified running build. No full benchmarks
requested; diagnose the actual generated browser module and click handler.

## Evidence before implementation

select_movie emits a flush inside the foreach body (from inlined collection At),
plus two afterward. The live fixture counts 14 DOM flushes per click. Across 12
choices: 168 flushes, ~136 ms spent in flush handling, ~11.7 ms average handler.
Temporary generated-host experiment defers selection flushes until the handler
returns, preserving the final state and all selection assertions. Result: 12
flushes, ~19 ms total flush handling, ~1.8 ms average handler, ~2.5 ms maximum.
These are browser diagnostics, not benchmark suite timings.

## Mechanism

Term inside an inlined member returns to its caller; it does not commit the
outer transaction. A scoped FunctionState flag suppresses only inline member
publication. Keep txn_name intact so existing collection proofs remain usable.
Restore the flag across nested calls. The outer transaction keeps its final
flush. No type, collection or app names are recognized by the compiler.

## Validation and documentation

Build the compiler and app, inspect the resulting handler for a single commit
flush, profile the generated module, test selection and the browser save flow.
Add a regression that collection reads inside a transaction do not publish
partial state. Run focused regression suites only at the final verification step.
Preserve all prior rationale; update frontend architecture and BUGS.md. Native
emission remains unchanged because the guard applies only to web publication.

## First emitted result

Inline-member scoping reduces actual selection from 14 flushes to 2 per click
(~2.1 ms average). Inspection finds bare term publishes once before its post
check and again in emit_bare_term_stop. Move publication/cleanup for bare term
entirely to its successful stop branch. Value terms retain their existing
completion path. This also prevents publication/cleanup when a bare term's post
is false, rather than treating duplicated effects as harmless overhead.

Removing the second flush exposed a register collision previously masked by
register numbering: callable-txn emission reset its shared temporary counter
AFTER allocating entry locals. Move that reset to function entry, so entry and
body use one monotonic register namespace. LLVM verification is the gate.

## Final app regression finding

The pending-peer gate exposed a wrong logout-confirmation contract, previously
hidden by premature publication: leave_with_pending_saves required the confirmation
flag to remain true, but logout clears it. Require authenticated confirmation at
entry and signed-out state at completion. Preserve the source contract rather
than restoring early publication to hide the violated postcondition.

## Verified emitted behavior

The rebuilt select_movie has exactly one flush call site. The generated browser
module (without the deferral experiment) records 12 flushes for 12 choices,
~1.2 ms average and ~1.6 ms maximum handler time in the fixture. Baseline was
14 flushes per click and ~11.7 ms average. Selection still applies synchronously,
with unchanged ratings/page and no transport request. Updated assets are served
by the already-running compiler-checkout demo on localhost:8081.

The pending-peer gate passes after correcting the logout postcondition and
making close-plus-submit run in one event turn (the prior fixture raced its
250 ms reconnect timer under compiler load). Coverage still includes optimistic
paint, duplicate/event ordering, fallback, failure, cancellation and stale login.
Release compiler rebuild and focused compiler regression gate run last.

## Final gate

Release compiler rebuilt successfully. Its emitted frontend IR byte-matches the
verified debug compiler IR. Final release assets profile at ~0.95 ms average,
~1.4 ms maximum handler time, with 12 flushes for 12 choices. Browser pending-peer
regression passes. Compiler crash regressions 9/9 and bare-term semantics 9/9
pass; Praetor has zero new diagnostics against the pre-change file baseline
(including the existing uncommitted pooled-object assignment work). No full
library rerun or benchmark suite was needed. The app remains served on 8081,
backend on 8080. Changes remain uncommitted under the teaching workflow.
