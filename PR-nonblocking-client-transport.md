## Add single-step nonblocking socket I/O and finite poll waits

Add Linux x86-64 stdlib primitives for event-loop clients: atomic nonblocking/
close-on-exec TCP creation, bounded one-call send/receive, pending connect error,
and an owned pollfd array with finite waits and explicit descriptor borrowing.

Sends retain caller-owned offsets, never retry internally, and suppress SIGPIPE.
Receives append only successful bytes; positive capacity makes zero mean EOF.
After EINPROGRESS readiness, SO_ERROR distinguishes successful connection from
failure. Poll clears stale events and returns EINTR so callers recompute deadlines.

Native controlled-peer tests cover partial writes, EAGAIN, EOF, success/refusal,
invalid descriptors, event clearing, idempotent poll cleanup, and eleven bounds/
lifetime rejections. No fixed port or external service is required. The feature
contains stdlib, documentation and tests only, with no compiler source changes.

The separate lifetime-proof PR enables bounded temporary reclamation during
repeated client operations. The separate tuple fix supports inferred socket
pair bindings in consuming programs. The native tests here use explicit values
and are also checked on this clean main-based feature branch.

API ownership and Linux ABI details are in docs/architecture/nonblocking-transport.md.
This is a transport foundation; HTTP framing, TLS, DNS and application load
campaigns are not part of these APIs.

Final clean-branch gates: 3,499 library tests passed with the source sweep delegated to CI; the native test covers three successful programs and eleven trapping cases; cargo build completed without warnings; Praetor passed. Lifetime proof PR: https://github.com/Randozart/briev-lang/pull/66. Tuple consumer fix: https://github.com/Randozart/briev-lang/pull/65.
