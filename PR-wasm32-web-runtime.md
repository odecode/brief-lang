Portable browser programs previously mixed target-native registers with fixed
64-bit boxed payloads, retained initialization stack addresses, and overflowed
fixed-size collection snapshots. Adapt values at the shared ABI boundaries,
retain persistent state on the heap, and resize view snapshots to actual size.
Preserve lexical foreach/enum payload types during operator elaboration and
propagate helper writes into browser DOM invalidation.

This is the main-based compiler/configuration carve-out. The portable stdlib
and browser host transport are separate on feat/portable-web-stdlib. The app is
separate on feat/recommender-frontend. Merge the existing generic-call literal,
match-terminating-arm and collection-rebinding fixes first; integration is the
verified combined execution surface.

Validation: independent cargo check --lib on this branch; native cache/server
gates and three server property tests; browser heap, actual WASM JSON and
1100-item Unicode snapshots; Chrome registration/login/rating/live/reconnect/
logout/mobile gate. Quick determinism passes; full corpus has six byte-identical
entries and the existing giantnode liveness rejection. clang-17 recommender OK;
other corpus rows retain missing-input/liveness limitations. Final full library
result is recorded in the portable-boundary plan; the accepted 38 environment
failures are compared by exact name and left untouched.
