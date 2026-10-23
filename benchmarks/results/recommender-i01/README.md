# I01 evidence inventory

`runtime-incomplete-archive.log` and its metadata preserve an initial run that
omitted the native acceleration/runtime archives from the private checkout.
Its acceleration link failure therefore differs from the real release setup.
**This is not the accepted complete runtime baseline.** The corrected archive
runner copies and hashes both assets; its full rerun is recorded separately.

`accepted-library-failures.txt` is the exact 38-name approved environment baseline,
copied before this assignment's library test run. Compare sets, not totals.

`runtime.log` and `runtime-metadata.json` are the corrected complete suite.
`release-build.log` records its clean release build. `app-metadata.json` identifies
the served source/compiler/binary/dataset hashes. Native single-owner, 20-owner
and 100-owner flow records, fixed-geometry browser records, blocked-DB/refresh
probes, protocol evidence and correlated server stages are preserved here.
The browser geometry records contain three warmups, ten measured edits and one
separately labelled new-rating transition each. Concurrent probes use one flow
per eligible owner. These are diagnostic baseline samples, not I16 acceptance.

Transient served binaries/snapshots remain in `/tmp/recommender-i01-app` (WSL);
screenshots/pilots remain under `target/recommender-i01-browser`. Owned app
services were stopped after measurement. Database briev_recommender_i01 is
retained; no existing user database was reset. Timeout outcomes remain unknown.
