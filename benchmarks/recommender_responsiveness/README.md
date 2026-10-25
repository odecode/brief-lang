# Production-path responsiveness baseline

I01 evidence and limitations are recorded in
`benchmarks/results/2026-10-22-recommender-i01-baseline.md` and the adjacent raw
inventory. The implemented I02 boundary is documented in
`docs/architecture/applications/recommender-responsiveness-contract-v1.md`.
To reproduce its native checks and build its browser fixture:

```bash
python3 benchmarks/recommender_responsiveness/contract_gate.py \
  --compiler ~/briev-target/debug/brievc --output /tmp/recommender-contract-v1
python3 -m http.server 18202 --bind 127.0.0.1 --directory /tmp/recommender-contract-v1/web
```

Run `contract_browser.mjs` with the generated HTML URL and an output JSON path
using the installed Playwright module. It exercises the real generated WASM
twice with runtime epoch inputs. The HTTP server is test-only and serves static
compiled output; all protocol/state checks execute in Briev.

These are test drivers, not replacement application/DB implementations. Run from
the repository root in WSL unless noted. Measurements are exclusive: finish
compiler builds/tests and the runtime suite before starting application timing.
Keep the current app services separate from ports 18082/18083 and database
`briev_recommender_i01`. Setup fails rather than deleting an existing database.

```bash
source ~/.cargo/env
CARGO_TARGET_DIR=~/briev-target cargo build --release
python3 benchmarks/recommender_responsiveness/runtime_baseline.py \
  --compiler ~/briev-target/release/brievc --commit 6fb27e01 \
  --output /tmp/recommender-i01-runtime
```

The archive runner copies and hashes both native runtime archives as well as the
release executable; Git archives exclude those build outputs. It preserves all
suite failures and normalizes shell CRLF only in its private checkout. The full
log and compiler/platform manifest are retained.
It does not overwrite tracked benchmark binaries. Its log is evidence even when
the existing suite exits nonzero; inspect every row before drawing conclusions.

```bash
# Once, as WSL root: narrowly scoped trust access and a fresh dedicated database.
bash benchmarks/recommender_responsiveness/setup_test_db.sh
python3 benchmarks/recommender_responsiveness/serve_baseline.py \
  --compiler ~/briev-target/release/brievc --output /tmp/recommender-i01-app
```

The service owner builds the authored server/browser, records binary/source/data
hashes and configuration, checks the catalogue, and owns only its two new child
processes. Interrupt it to stop them. It preserves database/artifacts for analysis.
The dataset is `.kiro/specs/recommender-app/u.data` (100000 records).

```bash
python3 benchmarks/recommender_responsiveness/native_baseline.py \
  --output /tmp/recommender-i01-native.json --samples 200
```

Native profiles begin with 0/4/5/20/100 persisted ratings. A zero-rating profile
necessarily becomes nonempty on its first save; output records the actual count.
Existing edits preserve other profile sizes; a separate new fifth rating is
reported. Every sample verifies owner, saved value, cold-start threshold, finite
score bounds, exclusion and deterministic top-five ordering. HTTP times are
client monotonic durations, never subtracted from server clocks. Three warmups
precede single-user samples. `--concurrency 20`/`100` runs independent account
streams (one operation outstanding per account), rather than idle sockets.
`--profile-count 5` makes every concurrent owner prediction-eligible. Use
`--prepare-only` to create separate browser profiles without measuring them.

On Windows, use Node with Playwright and installed Chrome:

```text
node benchmarks/recommender_responsiveness/browser_baseline.mjs URL USERNAME baseline-only OUTPUT.json 200
```

Use a generated profile username from the native output and URL
`http://localhost:18083/app.html?api=http://127.0.0.1:18082`. Set
`PLAYWRIGHT_MODULE` to an absolute installed module directory if required.
The test injects observation/correlation only, into the real generated app.
Warmups and measured edits use an existing movie so eligible profiles retain
their exact cardinality. The initially empty profile becomes a one-rating
profile. A final new-rating transition is logged separately with
`purpose=new_rating`; the four-rating account's transition is its first fifth.
It records browser-clock clicks, XHR start/end, live results, DOM mutations,
double-animation-frame paint opportunities and long tasks. CDP captures preflight
requests/status separately, without credentials or session query strings.

The current application has no pending feedback. Do not relabel its eventual
saved-rating paint as pending paint. A double RAF is a paint opportunity, not a
hardware presentation timestamp. Unchanged recommendation contents may require
no DOM mutation; match the fresh server calculation and received result as well.
Cold-start responses are never prediction throughput. Tail statistics from small
pilot samples are exploratory; the acceptance run uses at least 200 samples.

`RECOMMENDER_TRACE=1` enables bounded operation IDs and monotonic server stages.
Trace IDs are diagnostics, never account authority, deduplication, or revisions.
Default execution retains the synchronous path and existing wire responses.
Database wrapper durations include the Briev protocol/socket wait. The dedicated
database's PostgreSQL duration log separates database execution from those waits;
do not attribute the difference to prediction. Keep raw DB logs local.
