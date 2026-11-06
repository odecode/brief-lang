Tuple construction and destructuring merged all fields into one ownership memory set. Sending a tuple's clean buffer could therefore appear to expose pointers held only in an unrelated field:

```briev
let inner: Ptr = Malloc#(8);
let carrying: Ptr = Malloc#(8);
Store#(carrying, inner, 8);
let clean: Ptr = Malloc#(8);
let pair: (Ptr, Ptr) = (clean, carrying);
SysCall#(1, 1, pair.0, 8);
```

Track tuple slots with index-labelled FieldStore/FieldLoad constraints in `analysis/reclamation/walk.rs`, using the graph's existing field semantics. Apply this to construction, multi-name let bindings and recursive tuple patterns. Raw memory access still sees conservative aggregate contents.

Regression pairs select the clean or pointer-carrying field through projection, let destructuring and tuple patterns. A raw Load remains a barrier. In an integration workload parsing JSON objects and sending their textual keys, this removes the false sendto escape without hiding actual pointer exposure. The full authenticated client then reports zero lost bytes and zero Valgrind errors; that integration also uses the separate entropy and trait-default fixes.

Verification: 3,513 library tests pass (source-conformance sweep delegated to CI), including nested safe/escaping tuple patterns; cargo build has no warnings; no new Praetor diagnostics. The combined client completes five operations and independent SQL receipt checks with zero Valgrind errors, zero lost bytes and no open network sockets. Kani cannot start on this WSL glibc; no model-checking claim is made.

Based on upstream 9f49b2f8. No semantic merge dependency; the trait-default PR touches neighboring walker code. Bug record, ownership architecture and plan are included.
