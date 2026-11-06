## Prove temporary lifetimes around copying socket calls and concrete methods

Controlled native socket clients retained temporary object wrappers because the
reclamation analysis treated network calls and concrete method invocations as
unclassified effects. The change adds platform-configured synchronous socket
borrowing and call-graph edges for concrete explicit-receiver methods.

The socket rule is deliberately conditional for sendto: the flags must prove
MSG_ZEROCOPY absent. Linux retains zero-copy buffers beyond syscall return:
https://docs.kernel.org/networking/msg_zerocopy.html. Unknown, missing, mixed and
zero-copy flag sets remain capturing. Bounded bitwise constant propagation
supports flags such as `MSG_DONTWAIT | MSG_NOSIGNAL` without losing pointer
provenance; saturation becomes unknown.

Methods resolve by receiver type before free-function fallback. Unsupported
members retain their shadowing entry. Implicit receiver fields, generic members,
dynamic dispatch and chain back-references keep conservative behavior. Concrete
method bodies use the same escape graph as ordinary functions; returning an
allocation or retaining it in caller storage does not license reclamation.

The reproduction is a function allocating socket-address buffers, invoking
explicit-receiver byte-writing methods, then passing the address to a copying
connect/bind syscall. On the base compiler those wrappers survive the enclosing
call. With these proofs the controlled connect/refusal fixture frees them;
Valgrind reports zero errors and definite/indirect loss.

Regressions cover ordinary/zero-copy/dynamic flags, pointer provenance, lattice
saturation, returned method aliases and same-name member shadowing. A Kani
harness is included; local Kani cannot start because the executor lacks glibc
2.32–2.34. Executable tests and full-library results are recorded in the plan.

Based on upstream 84f37578. Independent of the tuple fix; the transport feature
can be reviewed separately. Configuration holds syscall numbers and flag masks;
no socket API or application name is recognized by compiler code.

Final gates: 3,503 library tests passed with only the CI-delegated source sweep excluded; cargo build completed without warnings; Praetor has no new diagnostics.
