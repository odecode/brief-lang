# Recommender task 10: parser and persisted population

Implement required steps 10.1, 10.3b, 10.4, and 10.6 in teaching increments.
Optional starred property/unit tasks remain unimplemented. The human runs the
toolchain and supplies each gate's output before the next increment.

1. Strict line-oriented u.data parser and canonical printer. Preserve timestamps,
   map identifiers once to zero-based indices, reject malformed/overflowing fields
   and out-of-range records without losing subsequent lines. Verify with a small
   example harness, including CRLF and an unterminated final line.
2. PostgreSQL schema and account/population identity mapping. Resolve the design's
   baseline user versus account foreign-key relationship explicitly; new accounts
   must never inherit baseline users' ratings. Verify DDL against the test DB.
3. Transactional baseline bootstrap: serialize the guard, insert the complete valid
   population, and mark completion only on success; roll back failures. Reload
   persisted data for the engine when already loaded. Verify two invocations.
4. Parameterized rating upsert scoped to account/item. Verify replacement in DB.

Documentation: add parser format/ownership comments, schema identity and transaction
invariants alongside their implementations, update the architecture description
when persistence is implemented, and record verified gates in tasks.md. Preserve
existing rationale comments. No compiler or performance change is planned.

Status: parser increment authored; execution gate pending human output.

2026-10-21 continuation: submitted resolver fix merged into
integration/ptr-provenance. Parser gate is green. Schema increment authored in
examples/recommender/store.bv with a small scratch/recommender_schema_gate.bv
harness. Baseline identities have their own baseline_ratings table; accounts
remain real login identities, with no dataset/account ID collision. Schema DDL
is transaction-owned, rolls back failures, and preserves the original error.
Design updated with the persistence boundary. Human says PostgreSQL is not set
up; typecheck/build and live DB verification remain pending.

2026-10-21 continuation: generic-call literal fix 367470ac merged into
integration/ptr-provenance as e14fd2c7. Only append conflicts in BUGS.md and the
net-stack log occurred; both fixes' entries were preserved. Required next gate:
human rebuilds the integration compiler, checks store.bv, and builds the schema
harness. Its original ptr/i64 error must be gone before PostgreSQL setup/live
schema execution. No database-bootstrap or upsert step is claimed complete.

Integration gate (2026-10-21): human's integration debug compiler build passed
without warnings, store.bv checked OK, and recommender_schema_gate linked
successfully. The full schema harness no longer emits the ptr/i64 type error.
Next teaching increment is local PostgreSQL installation/start, then a dedicated
role/database with a loopback-only, database/role-specific trust rule. Live
schema creation/repeat checks remain pending.

PostgreSQL environment (2026-10-21, human verified): Ubuntu package PostgreSQL
12, cluster main, port 5432, online under postgres. Data directory
/var/lib/postgresql/12/main; HBA /etc/postgresql/12/main/pg_hba.conf.
Next setup uses role briev_test and database briev_recommender_test, with a
first-match HBA rule scoped to that database, role, and 127.0.0.1/32. No global
authentication or listen-address changes. Role/database creation, HBA reload,
psql connection, and native schema gate remain pending human execution.

Live schema gate (2026-10-21): setup and execution completed by agent under the
human's clarified command split (human runs cargo/brievc only). PostgreSQL role
briev_test can login but is neither superuser nor createdb/createrole. Database
briev_recommender_test is owned by briev_test. HBA backup is
/etc/postgresql/12/main/pg_hba.conf.before-briev; first-match trust rule is scoped
to this database, role, and 127.0.0.1/32. HBA parser reports zero errors and
reload succeeds. psql confirms role/database. The compiled schema gate exits 0:
schema_created=true, schema_repeat=true, four_tables=true. Task 10.3b is green;
10.4 transactional/idempotent bootstrap and 10.6 scoped upsert remain next.

Task 10.4 increment 1 (2026-10-21): authored store_baseline_begin with explicit
READ COMMITTED, transactional marker INSERT ON CONFLICT DO NOTHING, then
SELECT done FOR UPDATE. It validates the one-row boolean response and leaves
the lock/transaction owned by the caller on success; failures roll back and
retain the original SQLSTATE/message via shared store_abort (also used by schema
creation). Guard alone cannot mark baseline done. Harness exercises two
acquisitions, rollback preserving prior marker state, deliberate division by
zero, SQLSTATE 22012 preservation, and post-error connection recovery. No data
inserts yet. Human check/build pending; agent will run the built harness.

Guard runtime gate (2026-10-21): built harness exits 1. marker_locked,
rollback_preserves_marker, marker_relocked, connection_recovers, and
failure_preserves_marker are true; original_error_preserved is false.
Do NOT mark the guard complete. Added pre/post-rollback PgResult diagnostics to
separate server-error decoding from rollback preservation. store_abort's IR
returns the original failure handle, as intended. Decoder/source inspection
has not yet established a compiler versus stdlib cause; no workaround applied.
Human rebuild of diagnostic harness pending, then agent runs it.

Guard verified (2026-10-21): direct brievc build/run authorized by human. Found
and fixed actual stdlib receive-length bug: sock_recv fills memory without
updating ByteBuf's value len. Added buf_received, published header/payload
lengths in pg_read_msg. Native harness exits 0 with all six checks true and
22012/division by zero retained before and after rollback. store.bv check OK.
The human runs only cargo commands; agent now runs brievc/check/build/run too.

Task 10 continuation (2026-10-21): integrated match termination fix as b0442ddd;
restored pg/bytes/Result fixes. Cargo build passes. Native object Result payloads
unwrap correctly; both wrong-side unwraps exit SIGILL as specified. Persisted
population passes exact small-fixture anchors and full 100,000-row dimensions,
terminal offsets, and both orientation sums. Missing/incomplete markers and SQL
errors recover the connection; completed empty snapshots are well formed.

Task 10.6: store_rating_upsert uses one parameterized account/item INSERT ON
CONFLICT, replacing rating and timestamp. Native gate passes replacement,
other-account and other-item isolation, missing-account SQLSTATE 23503, all input
bounds, unchanged rows after rejection, and caller-owned transaction rollback.
Durable Briev gates are in tests/fixtures/recommender with a WSL runner. Added
architecture ownership/transaction documentation; optional randomized property
work remains separate from these deterministic gates. Full integration suite and
durable corpus verification are running; no feature commit yet.
Final native gates (2026-10-21): all deterministic checks pass, including
SQLSTATE/message preservation before/after rollback, empty input preserving old
incomplete rows, late second-batch failure rolling back the first batch, and
last duplicate winning across batches. Two simultaneous native loaders yield
exactly one loaded=true/accepted=65 and one loaded=false/accepted=0, both reading
the same correct committed population. Praetor passes on examples/recommender,
lib/std/db, lib/std/net, lib/std, and tests/fixtures/recommender.

Upsert endpoint gate (2026-10-21): rating 1/5 and timestamp 0/9223372036854775807
round-trip through PostgreSQL. Required Task 10 lines are complete locally;
optional starred randomized properties are not claimed. Review handoff prepared
in PR-recommender-persistence.md, pending full suite and commit approval.

Final integration verification (2026-10-21): cargo build passes. cargo test --lib
finishes with 3164 passed and 38 failed; exact failure-name comparison against
the prior compiler-fix run adds none. Conformance reports only the known
examples/data-briev/adapters.dbvl positional-schema mismatch, not a recommender
source. The final durable native runner exits 0; the added upsert endpoint check
also exits 0. Required Task 10 steps and deterministic idempotent-load gate are
complete; optional randomized properties remain unchecked. No feature/stdlib
commit has been made; awaiting WORKFLOW.md's logical-unit commit approval.
Authorized commit/carve-out (2026-10-21): stdlib fixes are separate commits and
branches: db77a61b fix/pg-receive-length (base feat/net-db-postgres, because main
lacks the client) and dac3aa4a fix/result-wrong-side-unwrap (base main, compiler
23cbbdac prerequisite). Integrated as 5af1d7c0 and a1eb35bd. Standalone stdlib
regressions live in tests/fixtures/stdlib; Result gate moved there from the
recommender directory. Pending task-10 feature commit excludes lib/std changes.
