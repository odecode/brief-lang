# Close whole-file read descriptors on success and failure

`read_file` opened a file and returned `read_whole(...)` without closing the
descriptor. Repeated reads therefore exhausted descriptors even when the caller
had consumed every returned String. Both successful reads and read errors after
a successful open leaked the descriptor.

For example, repeatedly evaluating `read_file("/proc/self/stat")` increased the
lowest available descriptor on Linux. The regression also covers empty files,
a 20,000-byte file crossing growth boundaries, EISDIR from reading a directory,
and ENOTDIR from attempting to open a child of a regular file.

The wrapper now retains the read result, closes its descriptor, then returns
that original result. `read_whole` continues to own buffer growth. Open failures
still return immediately because no descriptor was acquired. Close does not
replace the original open/read result, and no close retry risks a reused fd.

The controlled 640-read probe fails on unchanged main and passes with this fix.
Valgrind reports zero errors and zero definite/indirect losses; only the existing
65,536-byte process-lifetime stdout buffer remains reachable. A native integration
test checks descriptor availability, content lengths and preserved error codes.

Final library and integration results are recorded in
`docs/plans/2026-11-05-collector-main-checkpoint.md`.

Based on upstream main 3737396b. No compiler or unrelated stdlib changes; no
merge dependency. Sustained process sampling should use this fix before relying
on its descriptor stability.

Final verification: 3,499 library tests passed with zero failures (the previously
delegated source sweep remains in CI); the native descriptor integration test
passed, cargo build completed without warnings, and Praetor passed both the
stdlib and changed regression files.

Minimal standalone reproducer (run the compiled program with a descriptor limit
of 64; unchanged main runs out of descriptors):

```briev
import "std/os/fs.bv";
let finished: Bool = false;
node main [!finished][finished] {
    foreach index in 0..640 {
        when is_err(read_file("/dev/null")) { endprogram 1; };
    };
    finished = true;
    endprogram;
};
```

Root cause and fix: `lib/std/os/fs.bv:109`, `read_file` returned the recursive
read helper directly after successful open. It now closes the descriptor before
returning the preserved result. The committed regression checks availability
without relying on a machine-specific descriptor limit.
