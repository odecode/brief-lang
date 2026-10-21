# Recommender task 10 gates

Run from WSL with PostgreSQL on 127.0.0.1:5432, a dedicated trust-auth role and
database, and the current integration compiler:

```bash
BRIEVC=/home/otto/briev-target/debug/brievc PGUSER=briev_test PGDATABASE=briev_recommender_test bash tests/fixtures/recommender/run.sh
```

The runner builds into a temporary directory. It checks parser semantics, object
Result payloads and both wrong-side traps, atomic/idempotent bootstrap, exact
small-population contents, missing/incomplete/error/empty population paths,
account/item upsert isolation, validation, foreign keys, caller transaction
ownership, late-batch rollback, duplicate keys across batch boundaries, and two simultaneous
startup loaders producing exactly one completed load.

It creates/resets only its own schemas: briev_bootstrap_gate,
briev_population_edge_gate, briev_upsert_gate, briev_batch_gate, briev_guard_gate, and briev_concurrent_gate. Do not run
concurrent copies against the same database. A failed run may leave its schema
for diagnosis; reruns expect their standard schema, without injected constraints
or renamed tables from an interrupted run.

Set FULL_BASELINE=1 to additionally reconstruct public.baseline_ratings and check
both orientations against its count and sum. This requires successful bootstrap;
it does not load or alter the public dataset. Full verification has also compared
all 100,000 persisted baseline tuples independently with the source u.data.