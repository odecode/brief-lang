# fix(backend): emit const String global as @str.N alias, not ptr null

## Summary

A module-level `const Name: String = "lit";` was emitted as `@Name = constant ptr null`. Every read of the const dereferenced a null pointer and segfaulted. This fix interns the constants literal and points the global at the interned `@str.N` struct, matching how body-level string literals resolve.

## The bug

Discovered building lib/std/net/http.bv (recommender-app Task 3): `WS_MAGIC` (the RFC 6455 handshake GUID, a const String) crashed ws_accept_key.

### Controlled A/B (discriminator)

- `client_key + "literal"` worked (produced a String of length 60).
- `client_key + WS_MAGIC` (WS_MAGIC being a const String) segfaulted.
- Emitted IR showed `@WS_MAGIC = constant ptr null`.

The discriminator: an inline string literal in the same concat works; only the const-String operand crashes. So the defect is the const-global emission, not string concat.

## Root cause

src/backend/llvm/mod.rs, two places:
- collect_strings_tl never scanned TopLevel::Constant, so a String consts literal was never interned into the @str.N table.
- The constant-global emitter had a stub `Quoted => null` arm, so the global was a null pointer regardless.

The [len][bytes] String header was therefore never allocated; dereferencing it crashed. The interpreter handled const String correctly (it is the reference), so this was codegen-only.

## The fix

1. collect_strings_tl now scans TopLevel::Constant so a String consts literal joins the interned @str.N table (the body-emission path relies on the same position lookup).
2. The constant-global emitter resolves the literals index and emits `@Name = constant ptr @str.N`, deduped by literal text (identical text yields one canonical global + aliases, matching the interned string-table identity).

Under opaque pointers @str.N yields a ptr, and protocol_llvm_type(String) is ptr, so `constant ptr @str.N` is a well-typed aliasing global. The empty-string sentinel (@str.0) is the sound fallback if a lookup ever missed. This mirrors body-level string literal resolution in emit_expr.rs - derived from the same table, not a special case.

## Tests

cargo test --lib green. Verified end-to-end by a scratch harness that reads WS_MAGIC and by ws_accept.bv computing the RFC 6455 known-vector accept (which concatenates the const GUID).

## Verification

- IR now shows `@WS_MAGIC = constant ptr @str.N` (not ptr null).
- ws_accept_key("dGhlIHNhbXBsZSBub25jZQ==") returns s3pPLMBiTxaQ9kYGzzhZRbK+xOo= (RFC 6455 vector).

## Merge order

Independent fix, cut from main; no dependency on the other two fix branches. The feature branch feat/net-stack-http-websocket depends on this fix (WS_MAGIC is a const String).

## Files changed

- src/backend/llvm/mod.rs: scan TopLevel::Constant in collect_strings_tl; emit the const-String global as an @str.N alias (dedup by text).
- BUGS.md: entry documenting the bug and fix.
