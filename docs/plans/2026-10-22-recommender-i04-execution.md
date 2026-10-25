# Recommender I04 execution note

2026-10-22. Status: implementation and standalone behavior gate authored;
compiler verification is blocked by this desktop's WSL access denial. Do not
mark I04's acceptance gate complete until the standalone runner passes.

I04 uses only the I02 contract records. `examples/recommender/profile_state.bv`
contains pure profile/list helpers, while `examples/recommender/admission.bv`
contains admission, hydration, prediction-tag, persistence, discard and eviction
transitions. No socket, SQL, child process or prediction calculation was added.
HTTP and live adapters can call the same `profile_admit` boundary.

Admission checks the owner/epoch/payload and reservation before mutation, enforces
profile, pending, receipt and retained-byte bounds, rejects repeated reservation
IDs, assigns a checked revision, and keeps ratings sorted on upsert. Exact
duplicates return the prior status; payload conflicts reject without advancing
the revision. The committed ratings base advances on commit, while the live
profile remains independent. Commit actions publish only saved status.

I02's frozen `ProfileAction` has no deferred enqueue action. I04 therefore keeps
later operation statuses in `PersistQueued` without an action, then emits the
next persistence intent after a head completes; I07/I10 still own the actual
serialized scheduling. Its dispatch, worker-tag binding and completion
boundaries reject attempts to bypass the earliest unresolved owner operation.
The discard transition requires no account worker to be active so a revision change cannot
strand a running job; the discard event follows tombstone commit. Prediction
invalidation is retained in profile state and drained after ordered writes settle.

Prediction transitions own and compare the full worker tag. An obsolete result
does not publish and, when it was the matching running job, requests the current
profile revision. Failed-head discard rebuilds from committed data plus later
unresolved operations, advances revision, invalidates changed prediction state,
and publishes the discarded event only after tombstone commit. Profile
eviction requires no unresolved owner operations; an evicted account with receipt
history must hydrate before another admission.

The new gate covers admission/revision, duplicate and conflict behavior,
cross-owner isolation, sorted edits, overload-before-acceptance, five-rating
cold-start threshold, saved-without-prediction, stale prediction completion,
failed-head discard, queued write ordering and idle/pending profile lifetime.
Run it with:

```bash
BRIEVC=/home/otto/briev-target/debug/brievc bash tests/fixtures/recommender/run_profile_admission.sh
```

`git diff --check` passed for the I04 sources and fixture. The dedicated runner
could not start: invoking `bash` attempted to launch WSL and Windows returned
`Wsl/ACCESS_DENIED`. A prebuilt compiler test binary exists in `target/debug/deps`
but Windows also denies executing it; `cargo` and `praetor` are not on PATH and
there is no Rust toolchain directory under the current user's standard install
location. Therefore Briev parsing, typechecking, native behavior, and Praetor
remain unverified, and no task checkbox is marked.

Files allocated to I04: `examples/recommender/profile_state.bv`,
`examples/recommender/admission.bv`,
`tests/fixtures/recommender/profile_admission_gate.bv`,
`tests/fixtures/recommender/run_profile_admission.sh`, this note, and the I04
section of `docs/architecture/applications/recommender-responsiveness-contract-v1.md`.

## 2026-10-22 prerequisite verification addendum

After the WSL executor became available, the first gate run exposed invalid
`term` statements inside expression match arms and a direct field access through
`AdmissionReservation`. Those were corrected using expression-valued matches
and the existing reservation helpers. The gate then exposed untyped list
literals in action and fixture struct fields; these now use explicitly typed
list bindings. The test's byte-cap case now fills valid reservations up to the
configured 64 KiB limit before checking rejection. Its FIFO assertion checks
that the second operation is blocked while the first is unresolved and becomes
dispatchable after the first commits. Discard keeps prediction pending without
emitting a prediction action, for the coordinator to drain after ordered writes
settle as specified by the v1 contract.

Verification: `brievc check examples/recommender/admission.bv` returned `OK`;
`BRIEVC=/home/otto/briev-target/release/brievc bash tests/fixtures/recommender/run_profile_admission.sh`
reported `profile_admission_code=0`, `save_without_prediction=true`,
`cold_start=true`, `stale_result=true`, `hydration=true`, `discard_code=0`,
`ordered_save_code=0`, and exited successfully. The linker emitted its existing
target-triple warning. I04 is integrated/verified for the standalone contract;
reactor integration remains I10.
