# Recommender I07 execution — durable receipts and ordered persistence

**Date:** 2026-10-22  
**Status:** integrated/verified  
**Plan of record:** `docs/plans/2026-10-22-recommender-responsiveness.md`  
**Contract:** `docs/architecture/applications/recommender-responsiveness-contract-v1.md`

## Goal and verified prerequisites

Implement the I07 durable database boundary and persistence worker policy using
the I02 worker/message contract and I04 admission state. Accepted in-memory
ratings remain independent of persistence. A worker reports saved only after a
successful commit; ambiguous commit outcomes reconcile through durable receipts.
No save completion launches prediction.

Before this work, I04's standalone gate passed after fixing its match-return,
reservation-boundary and fixture-capacity/FIFO defects. I05's model, real-process,
and framing gates passed with exit code 0. Evidence and commands are recorded in
`.kiro/specs/recommender-app/tasks-improvement.md` and the I04 execution note.

## Existing pipeline evidence

- `examples/recommender/store.bv` supplies the account/rating schema,
  parameterized rating upsert, and transaction rollback helper. Its schema and
  upsert transactions are not mutated by I07; the receipt relation is declared
  in the I07 module and installed in the isolated test schema.
- `examples/recommender/worker_messages.bv` validates the I02 `persist`,
  `receipt`, and `discard` payloads and saved/failed/receipt replies. Coordinator
  review extended `discard` with the original command and accepted timestamp;
  without these values a restarted worker cannot safely persist a tombstone.
- `examples/recommender/worker_pool.bv` currently returns an explicit
  `handler-unavailable` response for persistence. I07 builds a typed handler
  boundary consumed by coordinator wiring in I10; this task does not edit that
  I05-owned shared worker driver.
- `examples/recommender/admission.bv` owns accepted-operation identity and the
  pure FIFO phase transitions. I07 adds ready-head selection and retry timing
  for independent accounts without duplicating profile admission state.

## Design

The durable receipt key is `(account_id, operation_id)`. Receipts retain the
original epoch, global revision, item, rating, status (`saved` or `discarded`),
and timestamp until account deletion. Exact replay checks include the timestamp.
Account-row `FOR UPDATE` locking
serializes first writes, retries, and discards. The transaction checks the
receipt before touching ratings; a matching saved/discarded row is an idempotent
replay, while a payload mismatch is a conflict. A new normal write performs the
rating upsert and receipt insert in one transaction. A discard inserts a durable
tombstone without upserting the rating; a saved receipt cannot be discarded.
The existing population revision trigger runs in the same transaction as the
rating upsert.

Transport failures while a transaction is open, or a lost `COMMIT` reply, are
reported uncertain and require a fresh connection plus account-locked receipt
reconciliation. SQL errors with a known server response roll back and remain
definite failures. The worker never returns saved before `ReadyForQuery` confirms
COMMIT.

The pure dispatcher selects at most one unresolved head per owner while allowing
other owners to proceed. A failed or uncertain head blocks only that owner's
later writes. Retries preserve the operation ID and use bounded exponential
backoff from 100 ms to 10 s; exhaustion remains visible. Discard must pass
through the I04 tombstone transition before the next operation becomes eligible.

## Implementation steps

1. Add `operation_store.bv`: idempotent receipt schema setup, account-locking
   transaction helpers for save/discard, bounded receipt lookup, exact payload
   conflict handling, rollback/uncertainty classification, and saved/discarded
   response construction.
2. Add `persistence_worker.bv`: strict worker request validation and DB identity
   checks, worker-owned connection open/close, operation handling, receipt batch
   reconciliation, per-owner FIFO head selection, and bounded retry schedule.
3. Add a dedicated I07 DB fixture and runner that creates only its named schema;
   cover duplicate/replay, conflicting payload, retention, rollback atomicity,
   lost acknowledgement, older retry, discard tombstone, per-owner blocking,
   other-owner progress, and retry bounds. Keep the I04 no-prediction-on-save
   assertion as a separate prerequisite gate.
4. Update the contract implementation notes and task checklist. Preserve
   historical plan records and existing rationale comments.

## Verification and documentation

Run the new I07 runner against schema `briev_recommender_i07` with its own
`PGDATABASE`/`PGUSER` settings. Run direct `brievc check` on both new modules,
then the I04 and I05 prerequisite runners. Check the exact test output and exit
codes; no benchmark claim is part of this functional task. Update
`docs/architecture/applications/recommender-responsiveness-contract-v1.md`,
the I07 task status and this execution record after the gates pass.

## Results

**2026-10-22 results:** I04 and I05 prerequisite gates passed before I07 work.
The dedicated runner creates and removes only `briev_recommender_i07` in the
configured test database. It passed receipt replay/conflict (including changed
timestamp), lost-ack lookup from a fresh connection, older-retry protection,
durable discard replay, rollback atomicity, receipt batch retention across an
epoch change, worker
commit acknowledgements, and receipt replies. The pure scheduler gate passed
per-account FIFO, failed-head isolation, independent-owner progress, retry due
time, exponential delay and exhaustion checks. The shared responsiveness worker
contract gate passed its event/policy/message checks and 128 command/profile
cases. The runner removed its isolated schema and temporary binaries.

Commands:

```text
brievc check examples/recommender/operation_store.bv                         OK
brievc check examples/recommender/persistence_worker.bv                     OK
brievc check tests/fixtures/recommender/operation_store_gate.bv              OK
BRIEVC=... PGUSER=briev_test PGDATABASE=briev_recommender_test bash tests/fixtures/recommender/run_operation_store.sh
  duplicate_conflict=true lost_ack=true older_retry=true discard_tombstone=true rollback=true receipt_retention=true
  worker_commit_ack=true discard_tombstone_ack=true receipt_reply=true
  independent_account_fifo_retry_backoff=true
responsiveness_contract_gate
  commands=true counters=true profiles=true
  events=true policy=true workers=true
  protocol base contract passed (128 commands and profiles)
```
