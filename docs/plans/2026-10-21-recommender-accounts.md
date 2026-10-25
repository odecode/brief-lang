# Recommender account service (2026-10-21)

Task 11 builds on the verified task-10 store and pure-Briev PostgreSQL client.
The human confirmed that account_state returns authenticated identity/ratings;
task 12 composes recommendations using that same owner's engine row.

Implement and verify in small increments:
1. Credential validation and 32-bit FNV-1a byte hashing with known vectors;
   parameterized atomic registration and duplicate classification.
2. Parameterized login, opaque kernel-random session tokens, explicit caller-owned
   session table, and token resolution. Failed login must not create a session.
3. Token-authenticated state: every query scoped to the resolved account ID,
   public identity and ratings only, including empty and deleted accounts.
4. Deterministic native DB gates, >=100 generated validation/isolation cases,
   build/library suite, Praetor, and documentation. No performance claim.

Preserve exact credentials; whitespace-only inputs fail, surrounding whitespace
does not silently change an identity/password. FNV-1a is intentionally unsalted
and provides NO real credential security. Never expose stored hashes in public
account results. Session state must be explicit rather than hidden globals.
Use existing syscall/file wrappers, not host-language DB or token adapters.

Update account-service rationale comments, the application architecture doc,
local design/tasks, and net-stack ledger with API ownership and session lifetime.
Keep WORKFLOW.md unchanged. Compiler/stdlib defects, if found, follow separate
fix-branch PR flow. Ask before the completed logical-unit commit.

Native increments (2026-10-21): registration/login pass, including 144 credential
combinations, Unicode whitespace branches and FNV vectors. Session value-state
gate passes random-token format, stable owner bindings, failed issue/read paths
and immutable previous stores. State gate passes 120 generated two-owner cases,
empty accounts, deleted accounts, forged/restarted sessions and database error
classification/recovery. Final runner adds exact hexadecimal endpoints and a
claimed numeric ID token rejection. Cargo build and Praetor pass; full library
suite is running. No compiler or stdlib edits were needed.

Full-suite verification (2026-10-21): cargo build passes. cargo test --lib
finishes with 3164 passed, 38 failed; sorted failure-name sets exactly match
task 10. Conformance reports only the known adapters.dbvl schema mismatch.
Final native runner exits 0. Praetor passes on application and fixture dirs.
No compiler/stdlib edits or new defects were needed. The string fixture's
unsupported f/v escapes were corrected by constructing code points explicitly;
lexer.rs deliberately preserves unknown escapes, so this was not a lexer fix.
Fresh-connection persisted-state gate is the final added verification.

Final persistence gate (2026-10-21): after closing the first connection, a new
connection and empty session store log in and recover the exact persisted owner
ratings. All checks true, exit 0. Task 11 ready for logical-unit commit approval;
WORKFLOW.md unchanged. PR-recommender-accounts.md is prepared for the clean
feature carve-out after approval; the verified checkout remains integration.
