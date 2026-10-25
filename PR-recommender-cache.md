The similarity cache repeatedly recomputed base similarities and imputed cells;
full startup exceeded 37 minutes before cancellation. Reuse those prerequisites
without changing the original pair union or arithmetic order, persist a validated
whole-model snapshot keyed by transactional database revisions, and refresh in
an owned child process while continuing to serve the previous snapshot.

Observed full-dataset readiness is 11.8–15.3 seconds cold and 0.40–0.47 seconds
from a fresh persisted image. These are development observations, with direct
reference checks at the same geometry; the censored old run does not support an
exact speedup ratio. Version/length/dimension/key/checksum validation rejects
stale or corrupt snapshots. Failed workers/writes retain the served model.

This app-only branch builds on feat/recommender-server, includes its required
store source, and contains no compiler or stdlib changes. Merge earlier account/
persistence/population features and fix/wasm32-web-runtime and
feat/portable-web-stdlib prerequisites before running the combined app.

Validation: complete small-shape matrix comparisons and full-shape direct pair
checks; round trip/reuse/edit/delete/truncate/rollback/recreated-revision gates;
corruption/truncation/write failure; HTTP during a worker DB lock; queued refresh,
reaping and killed-worker retention; native server and property regressions.
The tracked cache plan and complete runtime ledger record results and limits.
