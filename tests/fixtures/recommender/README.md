# Recommender account gates

## Task 11 account gates

```bash
BRIEVC=/home/otto/briev-target/debug/brievc PGUSER=briev_test PGDATABASE=briev_recommender_test bash tests/fixtures/recommender/run_accounts.sh
```

This separate runner checks 144 credential combinations (including all Unicode
whitespace classes), FNV vectors, parameterized registration/duplicates/login,
explicit session ownership and token encoding, 120 account-isolation cases,
empty/deleted accounts, forged/restarted sessions, and database-error recovery.
It resets only briev_accounts_gate and briev_account_state_gate. Sessions are
process-local; credentials and ratings are PostgreSQL-backed. Recommendations
are composed by the server in task 12 using the same authenticated owner.
