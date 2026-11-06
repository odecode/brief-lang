A local entropy output buffer is conservatively marked as escaping because Linux x86-64 syscall 318 (getrandom) is absent from the configured synchronous-borrow set:

```briev
defn entropy() -> Int {
    let buffer: Ptr = Malloc#(16);
    term SysCall#(318, buffer, 16, 1);
};
```

Add the platform effect to `config/memory-effects.toml`. getrandom copies bytes before returning and never retains the output pointer, including partial/error results and dynamic flags. This is a declarative platform contract, not a special case in the ownership walker. See [getrandom(2)](https://man7.org/linux/man-pages/man2/getrandom.2.html).

The regression verifies dynamic flags remain borrowing, while an unclassified syscall still makes the caller a barrier. The existing memory-content escape rules remain active.

Verification: 3,512 library tests pass (source-conformance sweep delegated to CI), warning-free cargo build, and no new Praetor diagnostics. The combined authenticated client completes five operations with exact durable receipt checks, zero Valgrind errors and zero lost bytes. Kani cannot start on this WSL glibc; no model-checking claim is made.

Based on upstream 9f49b2f8, no merge-order dependency. Bug record, ownership architecture and plan are included.
