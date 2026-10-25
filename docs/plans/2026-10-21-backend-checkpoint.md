# Task 13 — integrated backend checkpoint

**Status: COMPLETE**, with the user's explicit acceptance of the existing 38
environment-related library failures. Optional unfinished tasks remain skipped.

The user authorized integrating completed task 12 and its compiler/stdlib fixes,
then completing every required task-13 gate. This session runs cargo and brievc
directly, superseding WORKFLOW's human-execution rule. Optional tasks stay skipped.

1. Preserve unrelated work; integrate the prepared collection-rebinding and
   floating Abs fixes as separate commits, then stdlib corrections and server.
2. Run the complete library suite and compare failures with the accepted baseline.
   The user explicitly accepts the 38 environment-related failures and instructs
   that they remain untouched. Resolve only newly introduced failures.
3. Verify required Tasks 1–12 gates together using the WSL compiler, dedicated
   PostgreSQL test database, native protocol/engine/cache gates and regressions.
4. Run build, directory Praetor and backend determinism guards. Record exact
   results and limitations; apply the user's accepted baseline to task 13.

Documentation: maintain the recommender task ledger, application/server and
backend architecture contracts, regression BUGS entries and fixture invocation
instructions. Preserve existing rationale comments and historical records.
This is correctness/integration work, with no performance claim.

## Integration

The integration branch is `integration/ptr-provenance`. Compiler fixes were
committed independently and merged normally: `d3684191` collection rebinding,
`507bf262` floating Abs. The standalone JSON fix is `14f7f666` on
`fix/json-parser-progress`, also merged. `f7a9cc29` carries the database import
scope and HTTP status-text corrections. Task 12 application commit: `c6434f7f`.
Its clean main-based app-only carve-out is `c8a45dea` on
`feat/recommender-server`; its diff contains no `src/` or `lib/` changes.
Append-only merge conflicts retained both sides' documentation and BUGS entries.
The integrated LLVM sources were compared with the verified starting working
tree: all five changed/new source files are text-equivalent.

## Required verification, 2026-10-21

Commands ran in WSL against the Windows source tree, using
`/home/otto/briev-target/debug/brievc`, `CARGO_TARGET_DIR=~/briev-target`,
`PGUSER=briev_test`, `PGDATABASE=briev_recommender_test`.

| Gate | Result |
|---|---|
| `cargo test --lib` | 3169 passed, 38 accepted failures; sorted failure-name comparison with the task-12 baseline is empty |
| `cargo build` | Pass, no Rust warnings |
| Daily-use ByteSink, socket loopback, net-stack helper golden tests | All three pass |
| Native dense reference and sparse CF engine | All oracle anchors, imputation, fusion, neighborhood truncation, exclusion/order/tie checks pass |
| Matrix/vector/IntVec and dual population probes | All checks pass, including 1682×1682 allocation and an integer above 2^53 |
| Engine cache | Similarity memoization, complete snapshot swap, signature invalidation, binary persistence and truncated-image rejection pass |
| `tests/fixtures/recommender/run.sh` | Parser, schema/bootstrap, population, upsert, batch rollback, concurrent startup and Result traps pass |
| `tests/fixtures/recommender/run_accounts.sh` | Credential, token ownership, account isolation and fresh-connection persistence gates pass |
| `tests/fixtures/recommender/run_server.sh` | Every native API, reactor, JSON, partial-write, HTTP/WebSocket lifecycle, owner isolation and refresh gate passes; existing three native properties each pass 128 cases |
| Native collection/Abs/PG receive regressions | Pass |
| Standalone stdlib `json_parse_gate.bv` | Five groups pass: literals, containers, strings, numbers and incomplete-input progress |
| Standalone `server.bv` build | Pass |
| Directory Praetor | Application, fixtures, db, net and stdlib pass |
| LLVM Praetor versus starting commit `2345b932` | Same diagnostic sites; existing `emit_statement` cognitive/cyclomatic metrics increase by one (818→819 / 278→279), as already recorded for task 12; new helper has no diagnostics |
| Quick IR determinism | All three corpus programs byte-identical across separate processes |
| Full IR determinism | Six admitted programs byte-identical; existing giantnode fixture is rejected by reactive-liveness admission before IR emission |

The full determinism script exits nonzero for giantnode and prints its generic
"DRIFT DETECTED" footer, but that row produced no IR to compare; no observed
IR mismatch occurred. This is the same admission limitation recorded in task 12.
Neither full LLVM Praetor nor the full determinism command is described as green.

The initial attempt to repair environmental test prerequisites was stopped at
the user's clarification. All such test-source edits were removed; the optional
validator build was stopped and the added emulator/validator packages removed.
No accepted failure was disabled, rewritten or fixed. No interpreter change,
frontend work, load simulator or performance task is included.
