Implement required task 14: a Briev browser UI for account creation/login,
catalogue and ratings, five-distinct-rating cold-start gating, and the latest
live recommendation set. Reconnect reloads persisted state with one owned
backoff timer; logout cancels it and closes the channel. JSON and application
state transitions remain Briev code.

This branch adds only app source and documentation above feat/recommender-cache;
it contains no compiler/stdlib source changes. Prerequisites are that cache/server
branch and the separately reviewed portable compiler and stdlib branches.
Optional task 14.4 is intentionally skipped.

Validation: Chrome against the native Briev backend passes registration/login,
duplicate-rating counting, five distinct ratings, cold-start visibility, latest
queued live updates, reconnect/state restoration, logout socket cleanup and
375px layout without overflow or page errors. The architecture document provides
WSL build/run commands and the separate frontend/backend listener addresses.
