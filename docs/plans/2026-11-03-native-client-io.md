# Native client I/O prerequisites

The load harness needs bounded progress across many sockets. Existing
`std/net/socket.bv` provides whole-transfer loops; `std/os/io.bv` is reserved.
Implement additive `std/net/nonblocking.bv` and `std/os/poll.bv` APIs entirely
in Briev, using existing syscall intrinsics. Preserve the existing blocking APIs.

Single-transfer send/receive return bytes moved, EOF or negative errno without
discarding earlier progress. Nonblocking connect completion reads SO_ERROR only
after readiness. Poll storage is bounded, reusable and explicitly released;
timeouts are finite and interrupted calls return to the caller for deadline
recalculation. No implicit retries or unbounded queues.

References: Linux man-pages connect(2), send(2), poll(2), consulted 2026-11-03:
https://man7.org/linux/man-pages/man2/connect.2.html
https://man7.org/linux/man-pages/man2/send.2.html
https://man7.org/linux/man-pages/man2/poll.2.html

Validate with Briev-controlled socket pairs: empty reads, partial transfers,
backpressure, readiness, peer shutdown, invalid descriptors, bounds and cleanup.
Add local TCP connect completion coverage with an ephemeral listening port.
Run native fixtures, library tests excluding the user-delegated conformance
sweep, build and Praetor. Update native-client-io architecture documentation
and append discovered defects to BUGS.md. This is correctness work; no
performance optimization or capacity measurement is claimed. Compiler runtime
benchmark baseline remains mandatory before any subsequent performance fix.

Validation checkpoint: native socket-pair and TCP success/refusal fixtures pass.
The bounds integration test passes all eleven invalid-input/lifetime cases and
the valid control. The full native load corpus is 10/10 green. Library suite:
3,438 selected tests passed (conformance delegated), matching debug build clean.
Praetor reports no diagnostics in the new modules. This remains transport
validation, not a completed load client or a performance result.
