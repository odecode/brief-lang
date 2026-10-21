# Recommender reactor, task 12.1

Implement the next teaching increment only: nonblocking listener, bounded
connection table and Linux x86_64 poll ABI. HTTP lifecycle/routing remains in
12.2 onward. No compiler optimization or performance claim is involved.

Use stable slots rather than indexing allocations by arbitrary fd numbers.
Slot zero is the listener; each other slot owns one socket. Keep authenticated
identity, live owner, upgrade state and input/output progress per slot. Kernel
pollfd records are exactly eight bytes (i32 fd, i16 events, i16 revents).
Full capacity disables listener interest until a slot is released; accept one
peer per sweep to preserve fairness. EINTR is retryable, errors remain explicit.

Verify native loopback acceptance, multiple clients, readiness, capacity,
slot reuse and clean teardown. Update tasks.md and document ownership/ABI in
docs/architecture/applications/recommender-reactor.md; preserve existing net
stack commentary. Run brievc check/build and Praetor per changed directory.
Commit remains subject to the teaching workflow's explicit approval requirement.

## Verification

WSL debug compiler checks the module without source warnings; native loopback
gate reports accept=true capacity=true nonblocking=true readiness=true
reuse_clears_owner=true removal=true invalid_config=true. Capacity test includes
a third client queued while both table slots are occupied. Kernel getsockname
selects an ephemeral test port. Existing linker triple warning is unchanged.
Praetor passes examples/recommender and tests/fixtures/recommender directories.
No compiler or stdlib files changed; full Rust library suite was not rerun for
this uncommitted teaching increment. Task 12.2 remains the next step.
