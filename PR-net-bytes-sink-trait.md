# feat(stdlib/net): ByteSink trait — fixed + growing byte buffers share derived writers

## Summary

`lib/std/net/bytes.bv` (net stack L1) now exposes one `ByteSink` trait so the two
byte-buffer flavors the wire protocols need — a **fixed-capacity** buffer and a
**growing** buffer — share their derived network-byte-order writers instead of
duplicating them.

## Motivation

PostgreSQL and HTTP need exact byte-level framing (big-endian multi-byte values,
NUL-terminated strings, arbitrary bytes a UTF-8 String cannot hold). Two buffer
shapes are needed:

- **Fixed** — a `put_*` requires room (`len < cap`) as a provable precondition and
  the pointer never moves. Needed for length-prefix backpatching (the Postgres
  wire protocol writes a placeholder length, then patches it) and allocation-free
  hot paths.
- **Growing** — a `put_*` always succeeds, reallocating when full. Ergonomic when
  the final size is unknown up front.

Both need the **same** derived writers (`put_u16_be`, `put_u32_be`, `put_cstr`,
network byte order). Duplicating that logic across two buffer types would be a
maintenance trap, so it is shared via a trait.

## Design

A single `trait ByteSink` (SPEC §8.6):

- **Required** (each implementer provides, with its own contract):
  - `put_u8(sink, val)` — write one byte
  - `put_bytes(sink, src_addr, count)` — bulk copy (`Copy#`/memcpy)
- **Default** (written once in the trait, over the required primitives):
  - `put_u16_be`, `put_u32_be` — big-endian multi-byte values
  - `put_cstr` — a String's bytes followed by a NUL terminator

Two implementers:

- `ByteBuf` (fixed) — `put_u8` keeps the `len < cap` room precondition; `put_bytes`
  keeps `len + count <= cap`; the pointer is stable (the buffer never moves).
- `GrowBuf` (growing) — `put_u8`/`put_bytes` have no room precondition; on overflow
  `grow_to_fit` reallocates (`Malloc#` double-or-enough, `Copy#` the live bytes,
  `Free#` the old block, return a new pointer).

Conformance is structural — an obj providing the required methods (with refining
contracts) satisfies the trait, no `impl` block. A function generic over
`<S: ByteSink>` therefore serves both buffers with one implementation.

```
defn frame<S: ByteSink>(sink: S, length: Int, label: String) -> S {
    let prefixed: S = put_u16_be(sink, length);
    term put_cstr(prefixed, label);
};
```

### Design notes

- The derived writers carry no explicit room precondition as defaults — the room
  obligation is enforced transitively by the required `put_u8`/`put_bytes`
  contracts, so a default stays pure over the primitives.
- A growing put MOVES the pointer. Length-prefix backpatching (a later task) must
  use the fixed `ByteBuf` or store offsets, never cached interior addresses — noted
  in the module.
- `Alloc#` is not supported by the LLVM backend; the buffers use `Malloc#`/`Free#`.

## Tests & example

- `tests/tier1/byte_sink_trait_smoke.bv` — end-to-end gate (auto-run by the tier1
  corpus). A generic `write_tagged<S: ByteSink>` writes a u16-BE tag + a
  NUL-terminated string into both a `ByteBuf` and a `GrowBuf` (the GrowBuf starting
  at cap 2, so the frame forces a mid-write realloc) and reads identical bytes back.
- `byte_sink_trait_golden_output` in `tests/daily_use_smoke.rs` pins the stdout
  (`18527210501852721050`) so a codegen regression is caught in CI.
- `examples/net-bytes-sink.bv` — a readable showcase of the same one-writer-two-sinks
  pattern.

Verified: both artifacts build, link, and run with the expected output; the three
golden tests (including the new one) pass.

## Dependency / merge order

`GrowBuf`'s growing path only compiles with two compiler fixes that this work
surfaced (both submitted as separate PRs, independent of each other and of this
feature):

1. **defn-liveness member-name collision** — a free-standing helper reached only
   through one obj's member was judged dead when another obj declared a same-named
   member first.
2. **type-dependent needs_state for monomorphized trait members** — a trait default
   monomorphized onto a type with stateful members was emitted stateless, producing
   an undefined `%state`.

**Merge both compiler fixes first**, then this feature branch (rebased on the
updated main) builds green.

## Files

- `lib/std/net/bytes.bv` — the `ByteSink` trait, `ByteBuf`, `GrowBuf`, readers.
- `examples/net-bytes-sink.bv` — the showcase.
- `tests/tier1/byte_sink_trait_smoke.bv` — the end-to-end fixture.
- `tests/daily_use_smoke.rs` — the golden assertion.
- `docs/plans/2026-10-09-fullstack-stdlib-and-net-stack.md` — L1 section + S1 ledger.
