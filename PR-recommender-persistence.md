# Add recommender baseline persistence and scoped rating writes

Task 10 now parses MovieLens u.data, creates the PostgreSQL schema, atomically
bootstraps a persisted baseline once, reconstructs the engine population from
persisted rows, and replaces account ratings at an account/item key.

Baseline identities are separate from real login accounts. Bootstrap serializes
startup loaders with a locked done marker; it imports bounded 64-record batches,
filters malformed/out-of-range lines, and uses the last valid duplicate record.
Missing/empty files and SQL failures roll back records and marker together.
Completed loads skip source access, including when the file is gone. The engine
adapter uses a repeatable-read snapshot and returns both sparse orientations
with all 943 baseline users represented.

Rating writes use bound parameters and one INSERT ON CONFLICT statement that
replaces rating and timestamp. Bounds and foreign keys reject invalid writes;
other accounts/items are unaffected. Existing transactions remain caller-owned.
Authentication and live account population updates belong to later tasks.

Depends on separately reviewed stdlib fixes fix/pg-receive-length and
fix/result-wrong-side-unwrap; neither stdlib edit is part of this feature commit.

Validation: cargo build passes; durable native gates pass parser boundaries,
object unwraps/both wrong-side traps, idempotency, exact small-population anchors,
error recovery, empty snapshots, batch-boundary rollback/duplicates, concurrent
startup (one load only), scoped replacement, validation/FK rejection, transaction
ownership, and rating/timestamp endpoints. Full baseline population has 100,000
ratings with both orientation counts/sums matching SQL. Independent comparison
matched every persisted tuple to the source u.data. Praetor checks pass.

Native runner: tests/fixtures/recommender/run.sh (dedicated local trust-auth test
database; its schemas are isolated from the public baseline). Full library suite: 3164 passed, 38 known failures, with no new failure names. Optional randomized property
tests remain unchecked.

Compiler fixes are excluded from a clean feature carve-out: relative imports,
generic call literal elaboration, and terminating match result preservation
are separate fix PRs. Verification runs on integration/ptr-provenance containing
those fixes. This integration vessel itself is not the feature PR branch.
Prerequisites not yet present on local main include the PostgreSQL client and
sparse rating_population stdlib modules from earlier feature work. A clean PR
carve-out must wait for or explicitly account for those prerequisite feature PRs;
it must not accidentally bundle the integration vessel's compiler history.

Clean feature branch: feat/recommender-persistence (19be337d), from main;
integration feature commit: 758f1d95. Post-carve native runner passes. Result
standalone regression belongs to tests/fixtures/stdlib on its separate fix branch.
