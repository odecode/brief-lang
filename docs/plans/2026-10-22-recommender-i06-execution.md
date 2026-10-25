# Recommender I06 execution record

2026-10-22. Status: **INTEGRATED/VERIFIED.** The original partial execution is
preserved below; current-compiler acceptance results are appended in the final
section. I06 is checked only after the real-snapshot comparison and memory gate.

## Evidence before implementation

The I01 production-path baseline uses the 943-user, 1682-item, 100000-rating
snapshot. Its single-owner stage traces measured active-build / prediction-scan
median times of 1.071 / 8.01 ms at five ratings, 3.420 / 13.19 ms at twenty,
and 14.114 / 24.64 ms at one hundred. These stages establish that active build
is material and grows with profile size; they do not isolate overlay copying,
CSR/means construction, and active similarity costs. They also show that the
scan remains a substantial cost. No overlay-copy speedup is inferred from the
aggregate stage.

## Implemented increment

The current active predictor now allocates candidate-similarity, deviation and
top-k marker storage once per request and reuses it for every catalogue item.
`knn_aggregate_reuse` clears only the active marker prefix and calls the same
selection routine as the allocating implementation. Candidate identities do
not participate in selection; traversal order and strict-greater tie behavior
are unchanged. `active_prediction_free` releases each workspace allocation
once after ranking.

`tests/fixtures/recommender/active_scratch_gate.bv` compares the allocating and
reused aggregator on zero candidates, fewer candidates than K, and forty
candidates with repeated score values. All three cases passed with the
release `brievc` available at `/home/otto/briev-target/release/brievc`.

## Remaining gate and observed build failure

The production active-profile view over immutable CSR/means is not implemented.
It must preserve the current replacement-row semantics and all prediction
equations; the I01 aggregate does not yet justify skipping those computations.
The controlled same-geometry A/B timing and exact IDs/order reference comparison
therefore remain open.

An attempted release build of `examples/recommender/server.bv` and
`server_loop_gate.bv` fails during clang verification with `Metadata id is
already used`. The generated IR declares `!99 = !{!"UInt64", !0}` and later
reuses `!99` for `distinct !{}` (`StateAliasScope`), so this is a numeric
metadata-ID collision in the current LLVM emitter output, not a Briev source
type error. Both `brievc check` commands pass, and the new standalone scratch
gate builds/runs successfully. Production timings and the real active-view
comparison are not claimed. Resolve the emitter collision before continuing
the production gate; do not record a timing from an unlinked binary.

## Continuation: prerequisite fix and controlled engine experiment

The earlier section misconverted the I01 active-build units: the baseline table
already reports milliseconds. Correct medians are **1071.43 / 3419.76 / 14114.46
ms** at 5 / 20 / 100 ratings; prediction scan is 8.01 / 13.19 / 24.64 ms.
The earlier 1.071 / 3.420 / 14.114 ms figures are incorrect. Active similarity
construction therefore dominates eligible prediction latency.

The compiler prerequisite now uses module metadata allocation after structural
type registration, including pending nodes across function resets. Its separate
record is `2026-10-22-module-metadata-allocation.md`. No new performance rule is
introduced in Rust.

The next experiment is a standalone Briev candidate, not yet selected by the
server. `active_profile_components.bv` reproduces the old build sequence and
separately times row copy, CSR build, means, and served user similarities. The
candidate retains immutable population base Pearson similarities once per
model/worker and uses a dense active-profile lookup plus the original observed
union. Old owner entries are skipped in every column, and the new active row's
imputation contribution is appended last, preserving accumulation order. Frozen
item-cache prediction remains exactly the current server algorithm.

Hypothesis: removing population copies alone will not explain the seconds-long
stage, but memoizing unchanged base similarities plus active imputation will
remove repeated calculation while preserving every score. One bounded workspace
allocation is reused across jobs, and output carries I02's exact worker tags.
The acceptance fixture compares every served user similarity, every finite fused
catalogue score, and the exact ranked IDs/order against the current overlay
engine at small edge shapes and the retained real snapshot. Full-shape reference
and candidate timings are interleaved three times per profile size after builds
finish, using one process, model, compiler and lambda.

## Current-compiler acceptance (2026-10-22)

The original I06 artifacts used a different compiler binary. The full runner was
rerun exclusively with release compiler SHA-256
`63c8b9689c63af8a601509a278f086cfd52466d56aa52f37338c1552376ccaa2` and the
retained I01 snapshot SHA-256
`bd5933a619292f8958f81176a44c626e111ee76c8477d927293bf953deafc623` (33,010,153
bytes). The edge gate passed for 1- and 40-user generated populations. On the
943-user/1682-item/100,000-rating snapshot, all three interleaved pairs at
0/4/5/20/100 ratings passed finite-score equivalence and exact ranked IDs/order;
the existing-owner exclusion case passed as well. The maximum mixed score error
was `7.75e-6`; served similarity error stayed at or below `5.96e-8`. The
reuse gate grew by one resident page after 100 repeated 100-rating predictions.

| Ratings | Reference mean ms | Active-view mean ms | Reference/view | Max error |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 72.114 | 10.237 | 7.04x | 0 |
| 4 | 821.679 | 19.398 | 42.36x | 3.22e-6 |
| 5 | 926.763 | 19.845 | 46.70x | 6.91e-6 |
| 20 | 2908.473 | 31.654 | 91.88x | 7.75e-6 |
| 100 | 12583.773 | 74.060 | 169.91x | 5.72e-6 |

These are isolated engine measurements, not browser/load acceptance claims. The
summary, raw logs, build logs and SHA-256 provenance are retained in
`benchmarks/results/recommender-i06-rerun-2026-10-22/`. The report script needed
one small path fix (`Path(__file__).resolve()`) to archive results when invoked
from the repository root; no engine code changed during this verification.
