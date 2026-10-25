# Add the recommender account service

Task 11 now registers and authenticates persisted accounts and returns an
account-and-ratings snapshot scoped to the authenticated session owner.

Credentials reject empty/whitespace-only inputs, including Unicode whitespace,
without trimming meaningful usernames/passwords. Registration uses a parameterized
INSERT ON CONFLICT to avoid duplicate-username races. Password storage is the
specified unsalted FNV-1a demo scheme and provides no real credential security.
Public account results expose only id/username, never passwords or stored hashes.

Login matches bound credentials and issues a 128-bit kernel-random opaque token.
The session table is explicit value state: the server captures the updated store;
failed login/SQL/entropy leaves the previous store unchanged. Tokens are process
local and invalid after restart. State resolves a token through that table and
uses one owner-filtered LEFT JOIN for identity and ordered ratings, including
zero-rating accounts. Deleted accounts/forged tokens fail auth; SQL failures stay
separate and retain their PgResult detail.

The human confirmed task 12 composes recommendations for that SAME engine owner;
this account-service state API does not fabricate a recommendation cache.

Validation: cargo build passes. Native run_accounts.sh passes 144 generated
credential combinations, all whitespace classes/FNV vectors, register/duplicate/
login cases, explicit session ownership, token hex endpoints, 120 generated
isolation cases, empty/deleted accounts, forged/restarted sessions, and SQL error
recovery. Praetor directory checks pass. Full library suite: 3164 passed, 38 known failures, with exactly the same failure names as task 10.

Dependencies: task-10 persistence feature and its existing PostgreSQL/sparse
population prerequisites; separate stdlib fixes fix/pg-receive-length and
fix/result-wrong-side-unwrap, plus their compiler prerequisites. This feature
changes no compiler or stdlib source. HTTP routing and recommendation composition
belong to task 12. Detailed API contracts are in the recommender-accounts
architecture document; native runner uses dedicated test schemas only.
A fresh PostgreSQL connection and empty session store also recover the exact
persisted ratings after login. WORKFLOW.md is unchanged.

Branch: feat/recommender-accounts, clean main-based commit ad6aea3e. Integration
commit: 2345b932. The PR contains one account-service commit and no compiler,
stdlib, or task-10 implementation history. Land task-10/dependency PRs first.
