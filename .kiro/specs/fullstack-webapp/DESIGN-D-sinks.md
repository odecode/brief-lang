# Design D: fixed + growing byte sinks over one ByteSink trait

## STATUS: COMPLETE (2026-10-15). Do not re-do. This is the record of how it was done.

D1–D5 all shipped and verified by running. `lib/std/net/bytes.bv` now exposes the
`ByteSink` trait (required `put_u8`/`put_bytes`; defaults `put_u16_be`/`put_u32_be`/
`put_cstr`) with two implementers: `ByteBuf` (fixed) and `GrowBuf` (growing). A
generic `<S: ByteSink>` serves both. En route the work surfaced + fixed TWO
compiler bugs (defn-liveness member-name collision; type-dependent needs_state for
monomorphized members).

Delivered as THREE fork branches (merge order: the two fixes FIRST, then the feature):
- `fix/liveness-member-name-collision` (PR-liveness-member-collision.md)
- `fix/needs-state-type-dependent-members` (PR-needs-state-type-dependent-members.md)
- `feat/net-bytes-sink-trait` (PR-net-bytes-sink-trait.md) — the clean stdlib PR
  (bytes.bv + examples/net-bytes-sink.bv + tests/tier1/byte_sink_trait_smoke.bv +
  the daily_use_smoke.rs golden + the net-stack plan S1 update).
See tasks.md "START HERE" for the live branch map and the next-task pointer.

---

**For the SECOND of two sessions.** PREREQUISITE: the bug in
HANDOVER-fix-trait-default-state.md must be FIXED and merged to main first
(monomorphized trait defaults must not emit a spurious %state). Verify the gate
below before building on trait defaults.

## Read first
1. .kiro/specs/fullstack-webapp/WORKFLOW.md  (environment, build, naming rule:
   NO single-letter variable names - use buf, val, addr, not b/v/p)
2. docs/plans/2026-10-09-fullstack-stdlib-and-net-stack.md  (the net stack plan)
3. lib/std/net/bytes.bv  (the existing L1 buffer - the thing we are refactoring)
4. docs/plans/2026-10-12-static-trait-generics.md  (how traits were implemented)

## Prereq gate (run before anything)
Rebuild if needed, then:
  ~/briev-target/debug/brievc build \\
    /mnt/c/Users/wotto/code/briev-lang/.kiro/specs/fullstack-webapp/scratch/probe_sink_generic.bv \\
    --out /tmp/g && chmod +x /tmp/g/probe_sink_generic && /tmp/g/probe_sink_generic
MUST print 2. If it errors with undefined %state, the fix is NOT in yet - STOP
and do the fix session first.

## The problem D solves
The net stack needs byte buffers in two flavors:
- FIXED capacity: a put_* requires room (len < cap) as a provable precondition;
  the buffer never moves (ptr stable) - needed for length-prefix backpatching in
  the Postgres wire protocol, and for allocation-free hot paths.
- GROWING: a put_* always succeeds, reallocating when full (ergonomic; size
  unknown up front).
Both need the SAME derived writers (put_u16_be, put_u32_be, put_bytes, put_cstr -
network byte order etc.). We must NOT duplicate that logic. Design D shares it via
a trait: the derived writers are trait DEFAULT methods written once; each buffer
type provides only the primitives (put_u8, raw copy) with its own contracts.

## Why a trait (not duplication, not a runtime flag)
Investigated 2026-10-12/15. The iterable protocol is deliberately structural, but
SPEC 8.6 traits are the right tool for USER generic behavioral abstraction. A
single obj with a growable: Bool flag was rejected: it collapses the contract
distinction (the fixed buffers provable room precondition is the whole point).
Two concrete types + one trait keeps per-type contracts AND shares logic.
VERIFIED the trait system supports this: two impls with DIFFERENT put_one
contracts (fixed room-precondition vs growing none) both satisfy one trait and
share a default - probe_sink_contracts.bv typechecks OK.

## Architecture

trait ByteSink (lib/std/net/bytes.bv or a new sink.bv):
  REQUIRED (each impl provides, with its own contracts):
    defn put_u8(sink: Self, val: Int) -> Self        // write one byte
    defn put_bytes(sink: Self, src_addr: Int, count: Int) -> Self  // bulk copy
  DEFAULT (written ONCE in the trait, built on the required ops):
    defn put_u16_be(sink: Self, val: Int) -> Self    // (val>>8)&255 then val&255
    defn put_u32_be(sink: Self, val: Int) -> Self    // 4 bytes MSB first
    defn put_cstr(sink: Self, text: String) -> Self  // bytes + NUL terminator

Two implementers:
  - ByteBuf (FIXED): put_u8 keeps [sink.len < sink.cap] precondition; ptr stable;
    put_bytes keeps [len + count <= cap]. (This is todays bytes.bv, retrofitted
    to provide the trait required methods; the current free-standing put_u16_be
    etc. become the trait defaults.)
  - GrowBuf (GROWING): put_u8 has NO room precondition; on overflow it Malloc#s a
    bigger block (double cap), Copy#s old bytes, Free#s the old, returns a ByteBuf
    with a NEW ptr + larger cap. (NOTE: growing moves ptr - callers must not cache
    interior addresses across a growing put. Backpatching callers use ByteBuf.)

## Trait syntax that WORKS (from the probes - copy these forms)
  trait ByteSink {
      defn put_u8(sink: Self, val: Int) -> Self;              // required: no body
      defn put_u16_be(sink: Self, val: Int) -> Self {         // default: has body
          let high: Self = put_u8(sink, (val >> 8) & 255);
          term put_u8(high, val & 255);
      };
  };
  obj ByteBuf {
      ptr: Int; len: Int; cap: Int;
      defn put_u8(sink: ByteBuf, val: Int) -> ByteBuf
          [val >= 0 && val <= 255 && sink.len < sink.cap]
          [term.len == sink.len + 1 && term.cap == sink.cap]
      { Store#(sink.ptr + sink.len, val, 1);
        term ByteBuf { ptr: sink.ptr, len: sink.len + 1, cap: sink.cap }; };
  };
Generic over any sink:  defn write_frame<S: ByteSink>(sink: S, ...) -> S { ... }
Conformance is structural (SPEC 8.6): an obj that provides the required methods
with refining contracts satisfies the trait - no explicit impl block needed.

## Known facts about the primitives (from the 1.1-1.5 work, all RUNTIME-verified)
- Malloc#(n) -> pointer held as Int; Free#(ptr as Ptr). (Alloc# is NOT supported
  by the LLVM backend - use Malloc#.)
- Store#(addr, val, width) / Load#(addr, width) ; addr arithmetic is plain Int +.
- Copy#(dest, src, count) = bulk memcpy (lowers to llvm.memcpy).
- A Briev String is [8-byte len][bytes][NUL]; byte count = text .^Length; the
  bytes start at ((text as Data) as Int) + 8. (The +8 was runtime-confirmed.)
- The proof engine proves shift/mask byte ranges and (hi<<8)|lo <= 65535 etc.

## Staged build plan (small increments, verify each by RUNNING, not just check)

Work on branch feat/fullstack-webapp-demo (the net-stack branch). Ensure it has
the trait-default fix (merge updated main first).

D1 - Define trait ByteSink with put_u8 required + put_u16_be default only.
     Make the EXISTING ByteBuf provide put_u8 as a member (move the free defn
     into the obj). Keep a tiny test: write_pair-style generic + direct call,
     build + RUN, confirm bytes/len correct.
D2 - Move the rest of the derived writers (put_u32_be, put_bytes, put_cstr) into
     the trait as defaults. Re-run the existing round-trip tests (the u16 BE
     byte-order test must still print 4660/18/52; put_cstr Hi must print 72/105/0/3).
D3 - Add GrowBuf: the growing implementer. put_u8 reallocs on overflow (Malloc#
     bigger, Copy#, Free#, new ptr+cap). Test growth: start cap 2, put 5 bytes,
     read them all back correct (proves the realloc+copy preserved data).
D4 - A generic writer used with BOTH ByteBuf and GrowBuf in one program - prove
     the SAME code path serves both sinks (the payoff of D).
D5 - Update docs/plans/2026-10-09-...-net-stack.md (S1 row): bytes.bv now exposes
     the ByteSink trait; note Alloc# -> Malloc# correction. Behavioral tests +
     a .bv example. Commit on feat/fullstack-webapp-demo, push to fork.

## Per-increment discipline (from WORKFLOW.md - the human is LEARNING)
- One small piece at a time; after each, STOP and explain what/how/why.
- brievc check for fast feedback, then BUILD + RUN (check alone misses codegen
  and layout bugs - that is how both the memcpy and this %state bug were found).
- Log any new compiler oddity in BUGS.md + the net-stack plan bug log, with the
  triggering .bv snippet.
- No single-letter variable names.

## Risks / watch-fors
- Growing moves ptr: never cache an interior address across a growing put. The
  Postgres length-prefix backpatching (future Task 3) should use the FIXED ByteBuf
  or store OFFSETS not addresses.
- >> on Int is a signed 64-bit shift; protocol values are non-negative by
  construction (fine), but keep masks (& 255) explicit.
- If a trait default needs a value only one impl can give, it is not a default -
  make it required. Keep defaults purely over the required primitives.
- Verify conformance diagnostics: a type missing a required method at a <S: ByteSink>
  call site should give a clear error (the trait branch added S4 conformance checks).

## Scratch probes (reusable, in .kiro/specs/fullstack-webapp/scratch/, git-excluded)
- probe_trait_3.bv        : generic <T: Counter>, prints 10 (baseline sanity)
- probe_sink_contracts.bv : two impls, different contracts, shared default (check OK)
- probe_sink_generic.bv   : THE bug repro (default via generic) - prints 2 once fixed
- probe_sink_nodefault.bv : required-method-only control - prints 2 (works pre-fix)
