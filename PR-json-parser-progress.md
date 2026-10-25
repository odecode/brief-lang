Fix JSON parser hangs on incomplete input and reject malformed separators,
tokens, escapes, Unicode scalars and out-of-range numbers. Recursive descent
maintains a consume-or-error invariant and requires complete input framing.
Named builder conversion imports keep the module composable with database users.

Standalone native regression: tests/fixtures/stdlib/json_parse_gate.bv, with no
recommender imports. All five grammar/progress groups pass under a timeout.
The complete server JSON/native integration gates also pass. Full library suite:
3169 passed and the same 38 environment failures explicitly accepted by the user.
Praetor passes the stdlib directory. No interpreter changes.

Branch fix/json-parser-progress, commit 14f7f666, is main-based and carries only
the stdlib correction, its native regression, plan and BUGS entry. Compiler fixes
collection-assignment-rebind and float-abs-intrinsic remain separate; the native
recommender feature is feat/recommender-server. Integrated verification and
limitations: docs/plans/2026-10-21-backend-checkpoint.md.
