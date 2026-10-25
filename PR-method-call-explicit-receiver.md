# Fix: dot-method dispatch to explicit-receiver obj members

## Symptom

Calling an obj member written in the **explicit-receiver** style (the first
parameter is the obj itself) through dot syntax reported a spurious type error:

```
// lib/std/net/bytes.bv:  defn put_u8(sink: ByteBuf, val: Int) -> ByteBuf
buf.put_u8(2)
  → type mismatch: expected ByteBuf for argument 0 of '.put_u8()', found Int
```

The free-function form `put_u8(buf, 2)` type-checked fine (it is how the
`ByteSink` trait defaults call `put_u8` INSIDE bytes.bv), and trait-DEFAULT
methods called by dot (`buf.put_u16_be(port)`) resolved correctly — only
concrete explicit-receiver obj members were broken through the dot form.

Found writing the L2 socket module (`lib/std/net/socket.bv`, recommender-app
Task 1), which builds the 16-byte `sockaddr_in` with the bytes.bv writers.

## Discriminator / controlled A-B

- `buf.put_u8(2)`  → ERROR (concrete explicit-receiver member, in `type_members`)
- `buf.put_u16_be(5432)` → OK (trait default, resolved via the conforming-trait path)
- `put_u8(buf, 2)` (free form, whole-module import) → OK

The split (member fails, trait default passes) pins the cause to the concrete
obj-member branch of method resolution, not the trait path.

## Root cause (file:line)

`src/typechecker/mod.rs`, `resolve_method_call`. The concrete-member branch
matched the written call args against member parameters starting at index 0.
For an explicit-receiver member, parameter 0 IS the receiver (`sink: ByteBuf`),
so the first written arg (`2: Int`) was compared against the receiver parameter
type (`ByteBuf`) — off by one. The `Type::Dyn` branch already handled this (it
computes `takes_self` and slices `&params[1..]`); the concrete branch had no
equivalent skip. Implicit-receiver members (`txn push(val: Int)`, no receiver
parameter) matched at index 0 correctly, so the gap went unnoticed.

## Fix (why it is sound, not a patch)

New helper `member_receiver_offset(params, type_name, name, supplied)`:
- returns offset 1 when the member's first parameter is the receiver (type
  `Self` or the obj's own type, via `first_param_is_receiver`), else 0 — the
  same rule the `Type::Dyn` branch uses;
- performs a sound arity check (`supplied == params.len() - offset`), so a
  same-type first parameter on an implicit-style member fails the count with a
  clear arity error instead of silently mis-skipping.

`resolve_method_call` indexes params from `offset`. The implicit-receiver path
(offset 0) is unchanged — additive. Extracting the logic into the helper also
keeps `resolve_method_call` from growing (net line reduction).

## Tests

- `typechecker::tests::method_call_explicit_receiver_member_resolves` — dot call
  to an explicit-receiver member type-checks.
- `typechecker::tests::method_call_explicit_receiver_arity_mismatch_errors` —
  too few args is a clear arity error.
- `typechecker::tests::method_call_on_obj_resolves` (pre-existing, implicit
  receiver) still passes — no regression.

`cargo test --lib typechecker` green.

## Verification

`brievc check lib/std/net/socket.bv` clean; the end-to-end loopback round-trip
harness builds and runs (`roundtrip_ok=true`).

## Merge order

Independent — no dependency on the void-call fix.
