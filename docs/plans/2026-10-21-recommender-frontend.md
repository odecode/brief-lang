# Task 14 — browser client and recommender frontend

**Status: ACTIVE.** Required substeps 14.1–14.3; optional 14.4 remains skipped.
The user authorizes toolchain commands, integration and the same focused branch
handoff as task 12. The 38 accepted environmental library failures are untouched.

1. Extend the browser host with method/body/content-type HTTP and managed
   WebSocket handles, message notification, send, status and close. Preserve the
   existing synchronous fetch(String)->String contract. Browser callbacks notify
   ordinary window events; Briev transactions own all application behavior.
2. Add typed stdlib HTTP and WebSocket wrappers. Add behavioral host/bridge
   regressions for transport failure, message ordering, handle isolation,
   intentional close and notification delivery. Verify actual wasm string ABI.
3. Build the .rbv application in small increments: credentials and login,
   authenticated state and movie choices, validated ratings, cold-start UI,
   most-recent live recommendation set and reconnect after unexpected close.
   JSON request encoding and response decoding remain Briev code using json.bv.
4. Verify the required frontend gate against the native backend in a browser,
   plus compiler/library, existing rbv and directory Praetor gates. Do not add
   optional property/load/performance work. Isolate compiler fixes if discovered.
5. Integrate focused compiler/stdlib/app commits; prepare clean carve-outs and
   PR-body drafts. Update task status and verification evidence.

Documentation: extend the browser host-boundary architecture and add
applications/recommender-frontend.md for launch instructions, event ownership,
wire behavior and reconnect semantics. Preserve prior rationale comments; log
surfaced compiler defects in BUGS.md with minimal regressions. No syntax change
is planned. No throughput or latency claim is made.

## Prerequisites discovered during the browser gate

The host transport behavioral gate passes (verbs, JSON error bodies, Unicode
strings, WebSocket FIFO/isolation/backpressure/lifecycle and timer cancellation).
The new linear-memory heap gate passes (growth beyond initial globals/stack,
coalescing reuse, realloc preservation, zeroing and invalid-size rejection).

The real JSON browser probe exposed target-width mismatches across collection
admission, captured process intrinsics, reflection, integer refinements, unary
operations, ordinary call/return adaptation, tuple/enum handles, foreach cursors,
string byte indexing, nested record addresses and pattern decoding. These are
being corrected at their shared lowering boundaries, preserving the i64 payload
layout while adapting native registers explicitly. No benchmark claim is made.
The native-only prelude and cast facade also require a portable split; the
browser selects it through target configuration. The decimal formatter requires
an explicit Int64 accumulator even when the target's flexible Int is 32-bit.

The app source now contains credentials, account state, movie catalogue, rating
submission, cold-start gating, latest live recommendations, one owned reconnect
timer with bounded backoff, and explicit logout cleanup. It is not accepted or
ready to push until the actual browser gate and compiler regressions pass.

## 2026-10-22 continuation

Chrome manual gate passed registration/login, duplicate movie updates remaining
one rating, five distinct ratings, cold-start visibility, latest two queued live
recommendation updates, reconnect with seven persisted ratings, logout socket
cleanup, and 375px layout without overflow. A compiler fixture additionally
checks initialized collection lifetime, Unicode and cardinalities beyond 1023.

The browser gate exposed state objects allocated in init_state's stack frame;
both empty and seeded initialization now retain heap instances. Collection
snapshots no longer have a fixed 1024-word limit. The renderer uses item identity
keys, actual UTF-8 item text and latest ordering. The larger compiler fixture
also exposed missing foreach element bindings during operator elaboration;
elaboration now shares the existing element-type authority and restores scope.

The full library run before the final lifetime/foreach increments had 3176 pass,
38 fail, with exactly the accepted task-13 failure names and no additions.
Final focused and library checks are pending after those increments.

## Final verification (2026-10-22)

The final full library run completed: 3178 passed, 38 failed, 743.48 seconds.
The failure-name set exactly matches the accepted task-13 baseline: no added
or removed failures. Both new lexical-scope regressions pass. Final release
build completed without new warnings, and its backend/browser artifacts built
successfully. The release frontend boots at localhost:8081 without page errors;
native backend OPTIONS and frontend HTML return HTTP 200. Compiler, stdlib,
cache and required frontend gates are complete; optional task 14.4 is skipped.
