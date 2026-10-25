# fix(analysis): propagate %state through a dot-call to a stateful obj member

## Summary

A free `defn` that invoked a stateful obj member through a DOT method call (`sink.put_bytes(src, n)`) was judged stateless, so its caller was emitted without the hidden `ptr %state` parameter, while the inlined member body referenced %state. clang rejected the IR with use of undefined value %state. This fix makes the MethodCall arm of the needs-state analysis consult the called members own statefulness.

## The bug

Discovered building lib/std/net/http.bv (recommender-app Task 3, the flagged trait-default-state risk): the response writers put_str helper calls sink.put_bytes(...), where GrowBuf::put_bytes reaches Malloc# via grow_to_fit (a stateful intrinsic path).

### Controlled A/B (discriminator)

- `defn app(sink: GrowBuf, ...) { term sink.put_bytes(src, n); }` FAILED (undefined %state).
- The free-function form `put_bytes(sink, src, n)` compiled.
- A direct `grow_new(...)` call compiled.

The discriminator: the MethodCall (dot) call site vs the Call (free) call site. Same callee, same statefulness; only the dot form lost the %state propagation. So the defect is in how MethodCall contributes to the needs-state verdict.

## Root cause

src/analysis/export_abi.rs: compute_defn_needs_state indexes obj members under type-qualified keys (GrowBuf::put_bytes) and the fixpoint computes their verdicts correctly. But the Expr::MethodCall arm of expr_needs_state only recursed into the receiver and args; it never consulted the called members own verdict. So a dot-called stateful member did not propagate %state to its caller. The 2026-10-15 member-indexing fix added the producer; the MethodCall consumer was the missing half.

## The fix

The MethodCall arm now ORs in a new helper method_is_stateful_on_any_type: the union over every indexed Type::method verdict. The MethodCall AST carries no resolved receiver type at this analysis stage, so the union is the sound over-approximation that type_stateful_members already relies on - if no types method is stateful the call is treated stateless (precise); if one is, the dot-call is treated stateful (conservative, at worst a harmless unused leading %state param). Derived from the indexed verdicts, not a blanket flip.

## Tests

- dot_call_to_stateful_member_forces_caller_state: a defn that dot-calls a member reaching Malloc# must take %state.
- dot_call_to_stateless_member_keeps_caller_stateless: a defn that dot-calls only a stateless member stays stateless (proves the fix does not blanket-flip every dot call).

cargo test --lib green.

## Verification

- put_str / the http.bv response writers compile (no undefined %state).
- http_response and http_json_response build a CORS JSON 200 end-to-end.

## Merge order

Independent fix, cut from main; no dependency on the other two fix branches (though it pairs with the 2026-10-15 member-indexing producer already on main). The feature branch feat/net-stack-http-websocket depends on this fix (the response writers dot-call GrowBuf members).

## Files changed

- src/analysis/export_abi.rs: MethodCall arm consults method_is_stateful_on_any_type; +2 regression tests.
- BUGS.md: entry documenting the bug and fix.
