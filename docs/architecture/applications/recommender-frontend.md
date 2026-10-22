# Recommender browser frontend

`examples/recommender/app.rbv` provides registration/login, a movie catalogue,
account-owned ratings, a five-distinct-rating cold-start gate, and the latest
WebSocket recommendation set. Movie numbers displayed in the UI are one-based;
the HTTP/WebSocket protocol uses zero-based item IDs. Updating an existing
rating does not count as another distinct movie. Logout closes the channel,
cancels the owned reconnect timer and clears account state.

## Run locally (Linux/WSL)

From the repository root, with PostgreSQL accepting the configured local test
role on 127.0.0.1:5432 and the MovieLens `u.data` file available:

```bash
source ~/.cargo/env
CARGO_TARGET_DIR=~/briev-target cargo build --release
~/briev-target/release/brievc build examples/recommender/server.bv --out /tmp/briev-recommender
PATH="/usr/lib/llvm-17/bin:$PATH" ~/briev-target/release/brievc build examples/recommender/app.rbv --split --out target/recommender-web
PGUSER=briev_test PGDATABASE=briev_recommender_test UDATA_PATH=/path/to/u.data /tmp/briev-recommender/server
```

In another terminal:

```bash
python3 -m http.server 8081 --bind 127.0.0.1 --directory target/recommender-web
```

Open `http://localhost:8081/app.html`. The backend defaults to port 8080.
An alternate backend can be selected with
`app.html?api=http://127.0.0.1:18080`. The frontend and backend have separate
listeners. The backend's `CACHE_PATH` controls its persisted model; a cold
start builds it before listening. See recommender-server.md for configuration
and refresh ownership. Run database gates only against a dedicated test DB.

## Host and lifetime boundaries

The browser prelude supplies portable casting/formatting and iterator modules,
without Linux process/environment/syscall lanes. `std/web/fetch.bv` retains
`fetch` and adds HTTP verb helpers over `fetch_method`. Requests return response
text synchronously because the current WASM String ABI cannot consume Promises;
JSON serialization/parsing remains Briev code. HTTP error bodies reach the app
for application diagnostics. This synchronous boundary can block the UI while
waiting for a response; asynchronous request ABI design is separate work.

`std/web/websocket.bv` wraps per-channel host handles. Each channel owns a bounded
FIFO (128 text messages / 1 MiB UTF-8), its error and event name. Queued browser
notifications recheck channel ownership, preventing a closed/logged-out channel
from emitting stale callbacks. Binary/oversized messages close the channel.
Unexpected closure starts one owned timer, backing off from 250 ms to 8 seconds;
reconnect reloads persisted account state before replacing the channel. Successful
open resets backoff. Each notification drains pending updates in order, so the
last received recommendation set becomes the displayed set.

The host allocator starts beyond initial WASM memory to preserve globals/stack,
grows by pages and coalesces free blocks. Realloc/calloc/copy/fill and String doors
share checked pointer/range handling. Boxed payload words retain their existing
64-bit layout while target-native registers and parameters use explicit casts.
Collection state objects are heap allocated so initialization frames cannot
invalidate their handles. View snapshots grow with actual collection cardinality;
they are consumed synchronously and reused within the WASM instance.

Frontend analysis computes possible global writes through direct helper calls
to a fixed point. Commit flushes consume these sets to update views. These are
conservative DOM invalidation sets, not concurrency or optimization proofs.
String item views decode UTF-8, render values, and reconcile DOM order to the
latest item order. Recommendation movie strings are unique identity keys.

## Verification

`tests/web_host_transport.mjs` covers HTTP verbs/error bodies, channel isolation,
FIFO/limits/lifecycle and timer cancellation. `tests/web_heap.mjs` covers memory
growth, stack isolation, coalescing, realloc, zeroing and invalid ranges.
Build `tests/fixtures/collection_snapshot.rbv --split` and pass the resulting
WASM to `tests/web_collection_snapshot.mjs` for persistent initialized state,
Unicode, more than 1023 items, snapshot reuse and reset. Native JSON encoding
has its own fixture, and browser JSON is checked with actual generated WASM.

The manual Chrome gate against the native backend covers registration/login,
duplicate-rating counting, five distinct ratings, cold-start visibility, latest
live recommendations, reconnect/state restoration, logout and a 375 px layout.
Optional task 14.4's application integration-test deliverable is skipped.
