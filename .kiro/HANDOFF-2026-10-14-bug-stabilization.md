# Handoff — compiler stabilization via BUGS.md (2026-10-14)

Written for the next fresh agent session. This records what was done today, the
state of each thread, and exactly where to pick up. Read the "Read first"
section before touching anything.

## Read first (orientation)

1. **`AGENTS.md`** (repo root) — the operating contract. Golden rules, the
   per-commit checklist, the Performance Recovery Protocol, git safety (never
   `git checkout --`/`restore`/`stash` someone else's work; new commits over
   amend; targeted `git add`). Non-negotiable.
2. **`.kiro/specs/fullstack-webapp/WORKFLOW.md`** — the build/environment manual.
   CRITICAL for this repo's split setup:
   - **Source of truth is the Windows tree** at `c:\Users\wotto\code\briev-lang`
     (edit here so the human sees it live in the IDE).
   - **Builds/tests run in WSL (Ubuntu-20.04)**, NOT on Windows. The cargo cache
     lives on the native Linux fs via `CARGO_TARGET_DIR=~/briev-target` (drvfs
     mtime churn on `/mnt/c` forces full rebuilds otherwise). A modern clang
     (clang-17) is required; stock 20.04 clang-10 can't parse the opaque-ptr IR.
   - WSL reaches the Windows tree at `/mnt/c/Users/wotto/code/briev-lang`.
   - The human runs the WSL commands; **give them the command, don't assume you
     can.** (You CAN drive WSL via `wsl -e bash -lic "<cmd>"` from the Windows
     shell, but see "Environment gotchas" below — stdout is often swallowed.)
3. **`BUGS.md`** — the bug ledger. Mostly historical/closed. The authoritative
   open set is tagged `[LEDGER 2026-10-06: OPEN]` / `[OPEN]` in the headers.

## Environment gotchas (learned the hard way today)

- The `execute_pwsh` → `wsl -e bash -lic` channel **often returns an empty
  result with exit code -1** even when the command succeeds. The `-1` is a
  display artifact, not a failure.
- **Reliable workaround:** have the WSL command write output to a file, then
  read it from Windows via the UNC path
  `\\wsl$\Ubuntu-20.04\home\otto\<file>` (or `\\wsl$\Ubuntu-20.04\tmp\...`)
  with the `read_file` tool. This bypasses the swallowed stdout entirely.
- Don't fire multiple long `cargo` commands in parallel — they contend on the
  build lock and it gets confusing. One build at a time.
- Prefer giving the human the command to run in their own terminal for long
  builds/tests; it's cleaner and keeps them in the loop (their stated
  preference).

## Standing build / test / run commands (WSL)

```bash
# full debug build (fine for correctness work; faster than --release)
cd /mnt/c/Users/wotto/code/briev-lang && source ~/.cargo/env \
  && CARGO_TARGET_DIR=~/briev-target cargo build

# fast type-check only
CARGO_TARGET_DIR=~/briev-target cargo check

# unit tests (whole suite, ~5 min). Filter with a substring: cargo test --lib <name>
CARGO_TARGET_DIR=~/briev-target cargo test --lib

# built binaries:
#   ~/briev-target/debug/brievc     (debug)
#   ~/briev-target/release/brievc   (release)

# build + run one .bv program:
~/briev-target/debug/brievc build <file.bv> --out /tmp/out && /tmp/out/<basename>
```

**Known-failing test baseline (do NOT chase these):** a full `cargo test --lib`
shows **38 failures** in this WSL environment, ALL environmental — PTX/SPIR-V/
cross-assembler tests needing GPU drivers / `ptxas` / `spirv-val` (absent here),
plus the pre-existing `adapters.dbvl` `.dbvl`-reader defect. A clean run is
"3025 passed, 38 failed" (the 3025 includes the +4 tests added today). If you
change code, A/B against this baseline: same 38 = no regression.

## Praetor (the complexity/verification gate)

- Praetor is now **installed in WSL** (`praetor` on PATH, built today from
  `github.com/Randozart/praetor-lsp`, cloned at `~/code/praetor-lsp`). It is a
  bespoke Rust LSP + verification toolkit, NOT a public crate.
- Per-commit gate (AGENTS.md): `praetor validate --warn --target <DIR>`.
  `--target` takes a **DIRECTORY, not a file** — a file silently passes without
  analyzing (exit 0). To check specific files, copy them to a temp dir and
  target that dir.
- The optional Semgrep/Infer/SonarLint bridges fail to auto-download in this
  env — harmless, they fail fast; the core complexity gate works without them.
  Append `2>/dev/null` to quiet the download chatter.
- The gate is **"no NEW diagnostics in changed files"**, NOT a clean tree.
  Pre-existing diagnostics on the big monoliths (`compile.rs` `compile_source`,
  `codegen`, etc.) are the project baseline. To prove zero-new, A/B: extract the
  pre-change files from git (`git show <sha>~1:<path>`) into a baseline dir, run
  praetor on both, diff the diagnostics keyed by function+rule (ignore line
  numbers — they shift).

## What was DONE today (shipped)

### 1. `.sbv` synthesizability gate — FIXED, pushed, PR-ready
- Bug: `src/hardware_validator.rs` was dead code (zero call sites). `.sbv`
  (Silicon) files using `Float`/unsized `Int`/`String`/`frgn`/`[true]`
  contracts silently passed checks the validator promised to enforce.
- Fix: `HardwareValidator::validate_silicon` + `enforce_silicon`, wired into
  BOTH `src/pipeline.rs` `parse_and_check` (check path) and `src/compile.rs`
  `compile_source` (build path). Plus `Statement::Let` handling and a sized
  `Int`/`UInt` `Constrained` arm in `check_type_synthesizable`.
- Branch **`fix/sbv-hardware-validator-gate`** — 2 commits (`588c87d7` fix,
  `bcac9d91` praetor refactor), **pushed to `fork`**. Verified: +4 tests, 0
  regressions, Praetor zero-new. PR description artifact was written (ask the
  human / check the artifact panel). **Not yet merged** — human will open the PR.
- BUGS.md entry flipped to `[RESOLVED 2026-10-14]` with a dated addendum.

### 2. Local `main` updated
- Local `main` fast-forwarded to `fork/main` (now at `74ba6742`, +18 commits).
  Note `main`'s configured upstream is `origin`, but it was updated from `fork`
  (they pointed at the same history; fast-forward was clean).

## The dialect model (important context)

Briev is one language with **target dialects** by file extension:
- `.bv` → CPU native binary (LLVM) — normal programs
- `.abv` → GPU kernels (PTX/SPIR-V) — "Accelerator"
- `.sbv` → **FPGA/ASIC hardware logic** — "Silicon" (yes, real hardware
  synthesis; that's why the gate rejects Float/unsized Int — no meaning on a
  chip)
- `.ebv` → embedded/MMIO firmware — "Electronics"
- `.rbv` → web/UI (WASM+DOM) — "Rendered"
- `.dbv`/`.dbvl` → data/schema

`SourceKind` + `classify()` live in `src/conformance.rs`.

## Open BUGS.md bugs — current status

Authoritative open set (headers tagged OPEN by the 2026-10-06 ledger):

### Group A — external, NOT fixable here (6)
GPU-driver / FPGA-toolchain / vendor issues needing real hardware + external
toolchains absent in WSL. Leave them:
- CIRCT ExportVerilog rejects `hw.module.generated`
- driver small-dispatch store loss (2–7 workgroups)
- coopmat S=1 produces zero y at 2048³
- CUDA 13.4 `cuMemcpy2D` no-ops under legacy-context dlopen
- NVIDIA driver 615.71.09 ~2.5× smem regression
- prime full-upload clobbers device arrays (has a mitigation; needs a GPU repro)

### Group B — compiler-side, fixable
1. **`hardware_validator` dead code** — DONE today (see above).
2. **LET-BOUND insert SSA-main segfault** (BUGS.md: "a node whose inserts are
   LET-BOUND"). INVESTIGATED today, **could NOT reproduce** with realistic
   programs. Every faithful repro (phased inserts + inline gets, with
   let-binding, modeled on the tracked `tests/tier1/test_hashmap_surface.bv`)
   prints the correct `10 20`. The failure only appears in a DEGENERATE node
   shape (let-bound inserts whose ONLY observable is inline gets, with NO
   anchoring state write). The original authors explicitly marked it "Out of
   scope" / "Pre-existing oddity (not a regression)" and it lives in the most
   regression-prone backend machinery (`defer_struct_allocas` + the
   `.ssb_<name>`/`@txn_go` dual-emission in `src/backend/llvm/loop_engine/ssa.rs`
   + `emit_expr.rs` `emit_tuple` const-tuple deferral). **Recommendation: leave
   it — high risk, low value, natural workaround exists (add any state write).**
   If revisited, you MUST first actually reproduce the segfault (find the exact
   no-anchor shape), then do a full IR A/B through the harness link BEFORE any
   code change (AGENTS.md Rule 20 — this whole bug family is a clang -O3/LTO
   interaction; source reasoning is insufficient).
3. **LLVM i64 Boxing Tax — Phase 1** ← **THE HUMAN'S CHOSEN NEXT TASK.**
   See the dedicated section below.
4. **nbody_newton 7th-decimal drift** — FP vectorization/reassociation parity
   vs a C reference. Needs the Performance Recovery Protocol A/B on actual `.ll`
   and ideally benchmarking hardware. Not started.

## NEXT TASK: LLVM i64 Boxing Tax — Phase 1 (bug #3)

The human wants to **make the LLVM backend correct even at large effort.** This
is the chosen thread. It was being scoped when the session ended — NO code
changed, NO branch created yet.

### What the bug is
The LLVM backend boxes ALL native types to a uniform i64 ABI for `%State`
storage (Bool `i1`→`zext i64`, Char `i32`→`zext i64`, Float `float`→`bitcast
i32`→`zext i64`, Float64 `double`→`bitcast i64`, String/Blob `ptr`→`ptrtoint
i64`). `TypedRegister.ty` tracks the BRIEV type, not the LLVM type, so the two
drift out of sync and emit invalid IR (`ptrtoint i8* %already_i64 to i64`,
`trunc i64 %i1`, etc.). This is the ROOT CAUSE of a whole family of BUGS.md
entries (float→Data→Int bitcast, tuple-String-as-i64, `%ac0` i64-vs-ptr, …).

### Current state (verified today — the BUGS.md 2026-06-16 entry is STALE)
- **Phase 0 (done 2026-06-16):** 18 sites patched so already-boxed values carry
  `Type::Int`. Documented in
  `docs/architecture/fixes/i64-boxing-type-confusion-phase0.md`.
- **A consolidation has ALREADY started** that the BUGS.md entry doesn't mention:
  `src/backend/llvm/builder.rs` has a `TypeConverter` with `box_to_i64` /
  `unbox_from_i64` (universe-driven via `Cast.String`/`Cast.Blob` properties,
  with a bootstrap-constructor fallback). This is the intended centralized
  box/unbox path ("Previously scattered across adapt_to_i64, native_float_or_box,
  and countless inline casts").
- **BUT the old scattered path is still pervasive:** `adapt_to_i64`
  (`src/backend/llvm/helpers.rs:2314`) and `ptrtoint_if_string`
  (`helpers.rs:653`) still have DOZENS of call sites across `emit_expr.rs`,
  `emit_stmt.rs`, `emit_toplevel.rs`, `helpers.rs`. So the codebase is MID-
  MIGRATION: a clean `TypeConverter` exists but most sites still use the old
  `adapt_to_i64` glue.

### Why the stale-entry warning matters
The BUGS.md "Phase 1 plan" says "delete i64 boxing entirely, native i1/i32/i8*
throughout, ~200 lines deleted." That was written 2026-06-16. Since then: the
String ABI was reworked (String = `ptr` to `[len][bytes]`), async ABI landed,
the collections/HashMap tuple redesign happened, and `TypeConverter` was added.
**Do NOT plan against the 2026-06-16 description.** Re-establish current ground
truth first.

### Recommended first moves for the next agent
1. **Investigate before planning (dispatch a context-gatherer).** Map the CURRENT
   boxing architecture: (a) is `%State` still a uniform `[N x i64]`, or have
   native-typed field slots been introduced (grep `field_types`, `StateChunk`,
   the `%State` struct emission)? (b) which sites still call `adapt_to_i64` vs
   the new `TypeConverter`? (c) what is the actual CURRENT invalid-IR risk — does
   the backend still emit bad casts, or did Phase 0 + the ongoing migration
   close most of it? Produce a current coverage map, NOT a replay of the 2026-06
   audit.
2. **Decide the real Phase 1 shape** from that ground truth. It is almost
   certainly NOT "delete all boxing" (the uniform-i64 `%State` may be load-
   bearing for the reactor/SSA model). More likely: finish migrating all
   `adapt_to_i64`/`ptrtoint_if_string` sites onto the single `TypeConverter`
   authority so the type tracking can't drift, and/or move `%State` to native-
   typed slots where sound. Scope it as a PLAN DOC first
   (`docs/plans/YYYY-MM-DD-i64-boxing-phase1.md`) per AGENTS.md rule 1.
3. **Write a plan with a baseline table** (AGENTS.md rule 12) — the 38-failure
   test baseline above, plus whatever benchmark/parity numbers matter if ABI
   changes could affect perf.
4. **Stage it** — this is a multi-commit architectural change. Small verified
   commits, `cargo test --lib` + Praetor each step, A/B vs the baseline. Create
   a fresh branch from `main` (e.g. `fix/i64-boxing-phase1`).

### Key files for bug #3
- `src/backend/llvm/builder.rs` — `TypeConverter` (the intended authority).
- `src/backend/llvm/helpers.rs` — `adapt_to_i64` (:2314), `ptrtoint_if_string`
  (:653), `string_ptr`, the binop/fcmp boxing.
- `src/backend/llvm/emit_expr.rs`, `emit_stmt.rs`, `emit_toplevel.rs` — the
  scattered call sites (state loads/stores, tuple/list elements, defn params,
  term values, etc.).
- `docs/architecture/fixes/i64-boxing-type-confusion-phase0.md` — Phase 0 record.
- `src/backend/llvm/tests.rs` — the Phase 0 regression tests (`test_bool_*`,
  `test_string_*`, `test_char_*`) — your "don't break these" set.

## Git state at end of session
- On branch **`main`** (clean tree), at `74ba6742`, 18 ahead of `origin/main`.
- `fix/sbv-hardware-validator-gate` pushed to `fork` (the day's shipped work),
  not merged.
- The investigation branch `fix/let-bound-insert-ssa-main` was deleted (it had
  zero commits — nothing lost).
- Scratch repro files and WSL temp artifacts were cleaned up.

## Do / don't recap
- DO investigate current ground truth before planning (several BUGS.md entries
  are stale — the ledger itself is a 2026-10-06 snapshot).
- DO keep the human in the loop; give them WSL commands to run.
- DO A/B against the 38-failure baseline and Praetor-zero-new before claiming
  no regression.
- DON'T chase the 38 environmental test failures.
- DON'T plan bug #3 against the 2026-06-16 BUGS.md description — it's stale.
- DON'T sink effort into bug #2 (LET-BOUND) — deferred by design, high risk.
- DON'T `git checkout --`/`restore`/`stash` others' work; new commits over
  amend; targeted `git add`.
