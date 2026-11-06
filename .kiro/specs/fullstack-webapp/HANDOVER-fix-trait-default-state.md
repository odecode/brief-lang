# Handover: fix the monomorphized trait-default %state codegen bug

**For the FIRST of two sessions.** This session fixes ONE compiler bug. A later
session continues the stdlib feature (see HANDOVER-design-D-sinks.md). Do NOT do
the feature work here.

## Read these first (in order)
1. .kiro/specs/fullstack-webapp/WORKFLOW.md  (environment, build strategy, rules)
2. AGENTS.md  (the repo operating contract)
3. BUGS.md  entry: Monomorphized trait DEFAULT method wrongly flagged state-taking
   (OPEN 2026-10-15) — the full diagnosis, repro, and fix direction.

## Environment (critical - from WORKFLOW.md)
- Edit source on the Windows tree: /mnt/c/Users/wotto/code/briev-lang (visible in IDE).
- Build with the cache on Linux fs:
    cd /mnt/c/Users/wotto/code/briev-lang && source ~/.cargo/env \\
      && CARGO_TARGET_DIR=~/briev-target cargo build        (debug is fine)
- TEST with ~/briev-target/debug/brievc. NEVER target/release/brievc (stale Oct 9).
- Fast inner loop: CARGO_TARGET_DIR=~/briev-target cargo check.
- clang-17 is the default (update-alternatives); clang-10 cannot parse the IR.
- Shell gotcha: commands go cmd.exe -> wsl; single-line only, write files with one
  printf of many quoted args; read results from files (host truncates streamed
  output). A fresh /tmp binary may need chmod +x before running (seen 2026-10-15).

## The bug in one paragraph
Static trait-constrained generics work (typecheck + run). But a monomorphized
trait DEFAULT method (a trait fn WITH a body, specialized per conforming type,
e.g. put_two\$FixedSink) is emitted taking a hidden ptr %state parameter, while
its correctly-stateless caller passes none -> clang: use of undefined value
%state. Required (body-less) trait methods are fine; only DEFAULTS break.

## Root cause (already located)
src/backend/llvm/emit_toplevel.rs, the S6 monomorphization emitter (comment
2026-10-13 static trait-constrained generics S6), ~line 3447:
    let needs_state = self.ctx.defn_needs_state.get(mangled).copied().unwrap_or(true);
    self.emit_definition(out, &specialized, needs_state);
mangled is the monomorphized name (put_two\$FixedSink), never registered in
defn_needs_state (only ORIGINAL fn names are) -> lookup misses -> unwrap_or(true)
-> state-taking. Caller is stateless -> undefined %state.

## Suggested fix (verify before committing to it)
Find where the ORIGINAL trait default/generic fn needs_state is computed and
reuse it for the monomorphized copy, instead of defaulting to true. Options,
best first:
1. When registering the mono copy, look up defn_needs_state under the ORIGINAL
   (unmangled) function name (strip the \$<Type> suffix, or thread the original
   name through the monomorphization call site) and use THAT.
2. Recompute needs_state from the specialized body via the same analysis the
   frontend uses (src/analysis/needs_state_projection.rs / export_abi.rs — see
   STATEFUL_INTRINSICS; a body that only calls defns + constructs a struct and
   touches no state field / stateful intrinsic is stateless).
Do NOT just flip unwrap_or(true) to false blindly — a trait default COULD
legitimately be stateful (e.g. call a txn / stateful intrinsic). Derive it.
Grep the needs_state machinery: defn_needs_state (populated where?), 
defn_takes_state(), and how the ORIGINAL generic defn (write_pair) already gets
the right verdict - the default fn should get the same treatment.

## Gates (must all pass)
A. Repro fixed: build + run probe_sink_generic.bv ->
     ~/briev-target/debug/brievc build .../scratch/probe_sink_generic.bv --out /tmp/g
     chmod +x /tmp/g/probe_sink_generic ; /tmp/g/probe_sink_generic   # expect: 2
B. No regression on required-method path: probe_sink_nodefault.bv still prints 2.
C. P3 still works: probe_trait_3.bv builds + runs, prints 10.
D. A STATEFUL trait default is still state-taking (write a probe: a trait default
   that reads/writes a program-state field or calls a txn — it must keep %state).
E. cargo test --lib green:
     CARGO_TARGET_DIR=~/briev-target cargo test --lib
   (expect the trait-generics behavioral tests from the trait branch to pass.)

## Add a regression test
Add a backend test (src/backend/llvm/tests.rs, near the other trait-generics
tests from branch feat/trait-system-implementation) asserting the monomorphized
trait default emits WITHOUT a spurious %state param (and the stateful case keeps
it). Model on existing trait tests.

## Git / branching (per AGENTS + prior sessions)
- This fix is independent of the stdlib feature. Create a bugfix branch FROM main:
    git checkout main && git pull   (ensure latest; traits are already merged to main)
    git checkout -b fix/trait-default-needs-state main
- Commit ONLY the compiler fix + its regression test. The .kiro/ docs and scratch
  probes are LOCALLY EXCLUDED (.git/info/exclude) - do not add them.
- Update the BUGS.md entry status OPEN -> FIXED <date> with the one-line fix summary.
- Push to the fork remote:  git push -u fork fix/trait-default-needs-state
  (origin = owner Randozart/briev-lang, no write access; fork = odecode/brief-lang.
   PRs from the fork may be restricted - if so, the human opens it / syncs to main.)
- The human merges the fix into main upstream when ready. The feature session will
  then pick it up from an updated main.

## When done
Report: the one-line root-cause, the fix, the five gate results, and that BUGS.md
is updated. Then STOP - the feature work is a separate session.
