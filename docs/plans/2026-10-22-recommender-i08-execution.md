# Recommender I08 execution — prediction workers and generations

**Date:** 2026-10-22  
**Status:** complete
**Prerequisites:** I05 and I06 integrated/verified.  
**Contracts:** `docs/architecture/applications/recommender-responsiveness-contract-v1.md`

## Goal

Connect the exact I06 active-profile engine to persistent I05 prediction
children. Coalesce only predictions (never persistence): each owner may have one
running request and one replaceable latest pending request. Fair scheduling lets
other owners progress. Every completion is checked against its full epoch,
revision, model-generation, job and attempt tag; stale results are dropped and a
settled latest profile remains dispatchable.

## Ownership and design

- New lane modules: `examples/recommender/prediction_worker.bv` and
  `examples/recommender/model_generations.bv`.
- Coordinator integration point: `examples/recommender/worker_pool.bv` only at
  the existing child-state/install/response boundary. The generic I05 framing,
  socket and lifecycle helpers remain unchanged.
- New gates: `prediction_pool_gate.bv` for deterministic scheduler/generation
  transitions; `prediction_pool_process_gate.bv` for real persistent child
  install, prediction, model replacement, shutdown and worker-death recovery.
- Reuse `active_engine_predict` and its per-worker workspace. Keep the current
  serial overlay engine as reference. Do not change prediction formulas or
  introduce score/result approximation.
- A generation lease is held by each installed worker and each running job.
  Replacing a worker generation acquires the new lease before releasing the old
  lease. Thus a descriptor cannot be reclaimed while a child or in-flight job
  still depends on it.

## Implementation steps

1. Add a parent-side prediction queue with one running and one latest pending
   request per owner, round-robin dispatch, full-tag completion checks, stale
   result suppression and bounded worker-death retry.
2. Add a generation registry built on I05's bounded model slots and reader
   leases; track each worker's installed generation and running-job leases.
3. Give prediction child state a reusable `ActiveProfileEngine`; install a new
   validated snapshot atomically, free the previous engine/model, and return a
   versioned `result` or bounded `error` for prediction requests.
4. Add pure and real-process gates for coalescing, out-of-order completions,
   worker death/restart, model swap/lease safety, exact scores/tags, bounded
   scratch reuse, and prediction progress while a separate DB request is blocked.
5. Update worker and prediction architecture comments in the same step. Do not
   edit shared server routing (I10) or browser files (I09).

## Verification

Run direct `brievc check` on both new modules and the process fixtures. Run the
I08 pure and process gates with a private model snapshot and I08-only IPC/socket
resources; also rerun the I05 worker lifecycle gate because its child response
path is being extended. Reuse I06's current-compiler equivalence and memory
evidence rather than timing another candidate. No browser/load performance claim
is part of I08.

## Results

Implemented the parent-side scheduler and persistent prediction child. The
scheduler accepts an explicit worker and owner capacity, latches one server
epoch until an idle-only reset, keeps at most one running and one latest
pending request per owner, scans owners round-robin, and reserves each running
worker ID so a stale readiness snapshot cannot assign it twice. It selects only
workers loaded with the request's model generation. Completed owners can be
evicted only after running and pending work clear, returning capacity without
losing accepted predictions. Completion validates the full tagged result/error,
clears terminal work, suppresses obsolete output, and leaves a newer pending
request ready for dispatch. Worker loss preserves newer pending work or retries
the current request with a bounded incremented attempt.

Each prediction child owns one reusable I06 engine. It builds a replacement
engine from a checksum-validated snapshot before freeing the prior model and
workspace. Child startup reports `started` only after the initial workspace is
available; allocation failure releases the partial state and exits without
advertising readiness. The protocol's `predict` payload now carries integer
`lambda_milli` in 0..1000 (500 default), and the child returns the standard
recommendations event with the complete issued tag. Generation leases are
tracked for workers and in-flight jobs. Repeated acknowledgements do not add a
lease; job release applies to the latest registry so concurrent installs are
preserved.

### Verification record (2026-10-22)

Compiler: `target/debug/brievc`, SHA-256
`6eb0c732193e0196e5a100878331babfc90fa7f9f136361e2010e295e8811009`.

```sh
RECOMMENDER_TEST_DATABASE_URL=postgresql://briev_test@127.0.0.1/briev_recommender_test \
  BRIEVC=target/debug/brievc bash tests/fixtures/recommender/run_prediction_workers.sh
BRIEVC=target/debug/brievc bash tests/fixtures/recommender/run_worker.sh
```

Both commands exited 0. The I08 runner printed passing results for fair owner
dispatch, stale-result suppression, latest-pending retention, bounded worker
retry, epoch rejection, terminal-error recovery, capacity refusal, generation
reader holds/reclamation, worker-local engine reuse, generation-2 replacement,
clean shutdown/reaping, crash/restart, timeout, malformed-frame isolation and
the framing regression. It also held a PostgreSQL advisory lock in one client,
blocked a second client on that lock, and observed
`prediction_completed_while_db_waiter_blocked=true` before cleanup. The I05
runner passed the same real process/framing lifecycle checks after the startup
ordering change.

I06's current-compiler reference/equivalence and 100-call scratch-memory gate
remains the numerical and memory bound: exact IDs/order, finite scores, and one
additional resident page. The I08 process fixture additionally reuses one
worker engine across consecutive requests. No browser or full-server latency
claim is part of I08. Generated outputs and logs are in the ignored
`target/recommender-I08/` directory.
