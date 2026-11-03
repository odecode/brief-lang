# Native client readiness and partial I/O

`std/net/nonblocking.bv` and `std/os/poll.bv` target Linux x86_64, matching the
existing raw-syscall socket module. The implementation is Briev, with no new
compiler intrinsics or foreign runtime.

Create a client with `sock_tcp_nonblocking()`, check its fd, then call
`sock_connect`. A zero result is immediate success; `-115` (EINPROGRESS)
requires waiting for output/error readiness and then calling
`sock_pending_error`. Zero from that function means completion succeeded;
negative values preserve the error. Reading SO_ERROR clears it, so capture
the result once. Calling it before readiness does not establish connection
completion. See the [Linux connect contract](https://man7.org/linux/man-pages/man2/connect.2.html).

`sock_send_once(socket, buffer, offset, count)` performs exactly one send,
preserving partial byte counts. It neither changes the buffer nor retains a
cursor. Advance your cursor only by positive returns. `sock_recv_once` appends
one receive into the buffer's free capacity and advances its logical length
only by positive returns. It requires positive capacity so zero unambiguously
means EOF. Both force nonblocking behavior for that call; send suppresses
SIGPIPE. EAGAIN (`-11`) and EINTR (`-4`) return control to the caller. Earlier
progress is never folded into an error or retried invisibly.

Construct a bounded `PollSet` with `poll_new`, configure each slot using
`poll_set` and inspect `poll_events` after successful `poll_wait`. Slots begin
disabled (fd -1). Events include error, hangup and invalid-descriptor bits
even when not requested. Hangup can accompany readable buffered bytes: drain
those before treating EOF as complete. `poll_wait` clears old events and
accepts only finite millisecond timeouts; on interruption recompute the
remaining time from the monotonic deadline. Scheduler delays can exceed a
requested timeout. See the [Linux poll contract](https://man7.org/linux/man-pages/man2/poll.2.html).

Poll storage does not own descriptors. Close sockets explicitly and call
`poll_free` once finished. Repeated frees through aliases of the same PollSet
are harmless; manually copying its raw address is unsupported. Construct
buffers and poll sets through their APIs and preserve their field invariants.
These objects require external synchronization if shared across threads.

The native gates verify partial sends under forced backpressure, byte-for-byte
receipt, EAGAIN without length mutation, EOF, disabled/invalid descriptors,
clearing old readiness, and TCP success/refusal using reserved ephemeral ports.
They establish transport correctness, not generator capacity or scalability.
