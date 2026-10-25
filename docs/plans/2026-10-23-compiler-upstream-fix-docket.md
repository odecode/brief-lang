# Recommender compiler fixes: upstream PR docket

**Status:** fixes are integrated in `integration/recommender-i10-i11`; no
upstream pull requests have been filed from this branch. This docket records
the defects, evidence, test coverage, and next PR preparation steps so the
compiler changes can be sent upstream independently of the recommender app.

## Branch and upstream context

- Integration checkpoint: `integration/recommender-i10-i11`.
- Recommender commits in this checkpoint: `c9f362a0` (I10/I11 wiring) and
  `77274523` (plan formatting), based on `a42faac5`.
- Repository remotes currently name `origin` as `Randozart/briev-lang` and
  `fork` as `odecode/brief-lang`. Confirm the intended upstream repository and
  its current base branch before filing PRs; no PRs are opened by this docket.
- This branch contains app, stdlib, docs and compiler work. Upstream compiler
  PRs should contain only the compiler fix, generic regression, compiler docs,
  and corresponding BUGS entry. Re-run the compiler gates on each extracted
  branch.

## Compiler fixes ready for independent PR preparation

| Bug | Fix and evidence | Current PR status |
|---|---|---|
| Float tuple destructuring bound boxed `i64` instead of unboxing the declared Float | Recommender oracle; inverse store/load representation fix; backend and native regressions | Draft: [`PR-float-tuple-destructure.md`](../../PR-float-tuple-destructure.md) |
| Raw `Ptr<T>` scalar indexing lost alias provenance across `inttoptr`, allowing stale reads after stores | Controlled LLVM IR A/B plus pointer load/store regression. The current correctness fix marks scalar accesses volatile; draft records optimization tradeoff and provenance-preserving follow-up | Draft: [`PR-ptr-index-provenance.md`](../../PR-ptr-index-provenance.md) |
| Reassignment of an ordinary local collection was treated as insertion | Generic collection rebinding semantics, fallback preservation and list regressions | Draft: [`PR-collection-assignment-rebind.md`](../../PR-collection-assignment-rebind.md) |
| Module metadata ID ranges overlapped (`!99` collision) and function resets lost pending module metadata | Shared module allocator after deterministic TBAA prefix; large-universe and cross-function metadata regressions | Plan/evidence: [`2026-10-22-module-metadata-allocation.md`](2026-10-22-module-metadata-allocation.md); no standalone PR draft yet |
| Eager LLVM `&&`/`||` evaluated guarded RHS expressions | I02 index-underflow discriminator, CFG/phi lowering, nested and termination tests, mutable local/parameter slot coverage | Plan/evidence: [`2026-10-22-logical-short-circuit.md`](2026-10-22-logical-short-circuit.md); no standalone PR draft yet |
| Reassigned mutable parameter slots reused LLVM SSA names | Real `sessions.bv` module regression checks unique local names after entry prologue allocation | BUGS and regression landed in `c9f362a0`; no standalone PR draft yet |
| Reactive rebinding of an unpacked top-level object dropped returned members | Recommender `server_step` LLVM regression checks member stores to registered instance slots | BUGS and regression landed in `c9f362a0`; no standalone PR draft yet |
| Browser-target portable value boundaries, target widths and persistent collection state | Target-width, boxed/native ABI, heap lifetime, dynamic snapshot regressions and browser gates | Compiler carve-out/evidence: [`2026-10-22-portable-web-boundaries.md`](2026-10-22-portable-web-boundaries.md); see also [`PR-wasm32-web-runtime.md`](../../PR-wasm32-web-runtime.md). Split compiler code from runtime/stdlib/host changes before upstream submission |
| Foreach and enum payload lexical types were lost during operator elaboration | Two unit regressions and generated-WASM collection fixture | Covered by [`2026-10-22-portable-web-boundaries.md`](2026-10-22-portable-web-boundaries.md); separate from browser host/runtime work when extracting |
| Print macro traversal skipped nested statements and operands | Exhaustive mutable postorder visitor; nested and error-path regressions | BUGS and `docs/architecture/ast-traversal.md`; no standalone PR draft yet |
| UTF-8 view text byte offsets drifted after multibyte characters | Accented/CJK/punctuation fixture before multiple directives | BUGS entry; likely belongs with view compiler/fullstack stdlib, not compiler-only unless view compiler is part of upstream compiler |

### Existing focused PR drafts

These root-level drafts describe fixes also encountered while getting the
recommender compiler path working. They are not submitted PRs. Review each
draft's referenced commit and gate before extraction:

- [`PR-const-string-global.md`](../../PR-const-string-global.md)
- [`PR-float-abs-intrinsic.md`](../../PR-float-abs-intrinsic.md)
- [`PR-generic-call-literal-types.md`](../../PR-generic-call-literal-types.md)
- [`PR-match-terminating-arm-values.md`](../../PR-match-terminating-arm-values.md)
- [`PR-relative-import-paths.md`](../../PR-relative-import-paths.md)
- [`PR-dot-call-stateful-state.md`](../../PR-dot-call-stateful-state.md)
- [`PR-method-call-explicit-receiver.md`](../../PR-method-call-explicit-receiver.md)
- [`PR-needs-state-type-dependent-members.md`](../../PR-needs-state-type-dependent-members.md)
- [`PR-trait-default-fix.md`](../../PR-trait-default-fix.md)
- [`PR-void-defn-statement-call.md`](../../PR-void-defn-statement-call.md)
- [`PR-liveness-member-collision.md`](../../PR-liveness-member-collision.md)
- [`PR-malloc-raw-memory-attr.md`](../../PR-malloc-raw-memory-attr.md)
- [`PR-lexer-cr-escape.md`](../../PR-lexer-cr-escape.md)

## Fixes that are not compiler PRs

The following work belongs in the application, standard library, or runtime
repository/lane, even though it was found while exercising compiler output:

- Recommender I10/I11 browser/server account API agreement; see
  [`2026-10-23-recommender-account-api-integration.md`](2026-10-23-recommender-account-api-integration.md).
- Persistence polling snapshot ordering, receipt schema migration, and user
  facing account/session behavior.
- HTTP, PostgreSQL, JSON framing/parser progress, and network byte sink drafts
  (`PR-net-*`, `PR-pg-receive-length.md`, `PR-json-parser-progress.md`).
- Portable web host and stdlib behavior in `PR-portable-web-stdlib.md`; split
  only the compiler-owned target-boundary changes into the compiler PR.

## Outstanding compiler issues, not fixed PR candidates

The following BUGS entries were still marked open at this checkpoint and must
not be described as fixed:

- WASM codec imports dead native assembly through closed reflection.
- Collection arrows retain unused task runtime.
- wasm32 typed Int constant emits an i64 load.
- Print macro inside foreach can reach codegen unresolved.

Check the current `BUGS.md` heading/status before acting on this list; later
work may have closed an item.

## PR preparation checklist

For each fix, create a clean compiler-only branch from the agreed upstream
base, cherry-pick or reconstruct only the relevant compiler sources, generic
regressions, architecture docs and BUGS entry, then run `cargo test --lib`,
`cargo build`, relevant focused gates, changed-directory Praetor, and the
applicable LLVM determinism gate. The recommender integration checkpoint has
not re-run Cargo tests; earlier user instruction was to continue without
waiting on them, with confirmation to follow. Revalidate every draft's claims
and commit IDs against the extracted branch before opening its PR.
